"""Motor (MongoDB) client, indexes, and id generation."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlparse

from bson.codec_options import CodecOptions, TypeCodec, TypeRegistry
from bson.decimal128 import Decimal128
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError, OperationFailure

from .config import get_settings


class _DecimalCodec(TypeCodec):
    python_type = Decimal
    bson_type = Decimal128

    def transform_python(self, value: Decimal) -> Decimal128:
        return Decimal128(str(value))

    def transform_bson(self, value: Decimal128) -> Decimal:
        return value.to_decimal()


_CODEC = CodecOptions(type_registry=TypeRegistry([_DecimalCodec()]))

log = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None
_connected_db_name: str | None = None


def now() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(dt: datetime | None) -> datetime | None:
    """Normalize MongoDB datetimes (often naive UTC) for aware comparisons."""
    if dt is None or not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _db_name_from_url(url: str) -> str | None:
    """Extract database name from connection string path, if present."""
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    return path.split("/")[0] or None


async def init_db() -> AsyncIOMotorDatabase:
    global _client, _db, _connected_db_name
    if _db is not None:
        return _db
    settings = get_settings()
    db_name = _db_name_from_url(settings.database_url) or settings.mongodb_database
    _client = AsyncIOMotorClient(
        settings.database_url,
        serverSelectionTimeoutMS=5000,
        maxPoolSize=50,
        minPoolSize=5,
        retryWrites=True,
    )
    _db = _client.get_database(db_name, codec_options=_CODEC)
    _connected_db_name = db_name
    log.info("MongoDB connected — database=%s (NODE_ENV=%s)", db_name, settings.node_env)
    await _ensure_indexes(_db)
    return _db


async def _create_index_migrate(
    collection,
    keys,
    *,
    index_name: str | None = None,
    **kwargs,
) -> None:
    """Create index; on spec conflict (code 86), drop same-named index and retry."""
    try:
        await collection.create_index(keys, **kwargs)
    except OperationFailure as exc:
        if exc.code != 86:
            raise
        name = index_name
        if not name:
            key_list = keys if isinstance(keys, list) else [(keys, 1)]
            name = "_".join(f"{k}_{d}" for k, d in key_list)
        try:
            await collection.drop_index(name)
        except Exception:
            pass
        await collection.create_index(keys, **kwargs)
        log.info("Recreated index %s on %s", name, collection.name)


_MISSING_ID_QUERY = {"$or": [{"id": {"$exists": False}}, {"id": None}]}


async def _backfill_missing_int_ids(
    db: AsyncIOMotorDatabase,
    collection,
    *,
    counter_name: str,
) -> int:
    """Assign next_id() to legacy rows that never stored an app-level id."""
    n = 0
    async for doc in collection.find(_MISSING_ID_QUERY):
        await collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"id": await next_id_for(db, counter_name)}},
        )
        n += 1
    if n:
        log.info("Backfilled %s missing id(s) on %s", n, collection.name)
    return n


async def _ensure_unique_id_index(
    db: AsyncIOMotorDatabase,
    collection,
    *,
    counter_name: str | None = None,
) -> None:
    """Unique integer id — backfill legacy nulls before building the index."""
    counter = counter_name or collection.name
    await _backfill_missing_int_ids(db, collection, counter_name=counter)
    indexes = await collection.index_information()
    info = indexes.get("id_1")
    if info and info.get("unique"):
        return
    try:
        await collection.create_index("id", unique=True)
    except DuplicateKeyError:
        await _backfill_missing_int_ids(db, collection, counter_name=counter)
        await collection.create_index("id", unique=True)
        log.info("Created unique id index on %s after backfill", collection.name)


async def fetch_users_by_ids(db: AsyncIOMotorDatabase, user_ids: list[int]) -> dict[int, dict]:
    """Batch-load users by id (avoids N+1 in admin list endpoints)."""
    ids = list({i for i in user_ids if i is not None})
    if not ids:
        return {}
    out: dict[int, dict] = {}
    async for doc in db.users.find({"id": {"$in": ids}}):
        out[doc["id"]] = doc
    return out


async def _ensure_sparse_unique_index(collection, field: str) -> None:
    """Unique sparse index — recreate if an older non-sparse index blocks multiple nulls."""
    name = f"{field}_1"
    indexes = await collection.index_information()
    info = indexes.get(name)
    if info and info.get("unique") and info.get("sparse"):
        return
    if info:
        try:
            await collection.drop_index(name)
        except Exception:
            pass
        log.info("Dropped legacy index %s on %s (recreating sparse)", name, collection.name)
    await collection.create_index(field, unique=True, sparse=True)
    log.info("Ensured sparse unique index %s on %s", name, collection.name)


async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    # Integer id (primary app key) — one unique index per collection that uses next_id()
    for coll in (
        "users",
        "markets",
        "presets",
        "market_bets",
        "crypto_bets",
        "otp_codes",
        "sessions",
        "admin_sessions",
        "redeem_codes",
        "crypto_payments",
        "blik_deposits",
        "blik_withdrawals",
        "casino_rounds",
        "wallet_ops",
        "blackjack_sessions",
    ):
        await _ensure_unique_id_index(db, db[coll])

    await db.isports_auto_sessions.create_index("id", unique=True)

    await db.users.create_index("username", unique=True)
    await db.users.create_index("created_at")
    await _ensure_sparse_unique_index(db.users, "telegram_id")
    await _ensure_sparse_unique_index(db.users, "discord_id")
    await db.users.create_index("referred_by_id", sparse=True)
    await db.otp_codes.create_index([("user_id", 1), ("used_at", 1)])
    await db.otp_codes.create_index(
        [("provider", 1), ("lookup_key", 1)],
        unique=True,
        partialFilterExpression={"used_at": None},
    )
    await db.rate_limits.create_index("expires_at", expireAfterSeconds=120)
    await db.otp_lockouts.create_index("locked_until", expireAfterSeconds=0)
    await db.redeem_lockouts.create_index("locked_until", expireAfterSeconds=0)
    await db.sessions.create_index("token_hash", unique=True)
    await db.sessions.create_index("user_id")
    await db.admin_sessions.create_index("token_hash", unique=True)
    await db.redeem_codes.create_index("code", unique=True)
    await db.redeem_codes.create_index([("kind", 1), ("created_at", -1)])
    await db.crypto_bets.create_index([("window", 1), ("window_start", 1), ("status", 1)])
    await db.crypto_bets.create_index([("user_id", 1), ("created_at", -1)])
    await db.crypto_bets.create_index([("user_id", 1), ("status", 1), ("created_at", -1)])
    await db.crypto_bets.create_index(
        [("slip_group_id", 1), ("user_id", 1)],
        sparse=True,
    )
    await db.casino_rounds.create_index([("user_id", 1), ("created_at", -1)])
    await db.casino_rounds.create_index([("game", 1), ("created_at", -1)])
    await db.casino_rounds.create_index("created_at")
    await db.crash_history.create_index("updated_at")
    await db.wallet_ops.create_index([("user_id", 1), ("created_at", -1)])
    await db.crypto_payments.create_index([("status", 1), ("created_at", -1)])
    await _create_index_migrate(
        db.crypto_payments,
        "derivation_index",
        index_name="derivation_index_1",
        unique=True,
        sparse=True,
    )
    await db.crypto_payments.create_index(
        [("kind", 1), ("asset", 1), ("status", 1), ("created_at", 1)]
    )
    await db.crypto_payments.create_index([("kind", 1), ("created_at", -1)])
    await db.crypto_payments.create_index(
        [("kind", 1), ("status", 1), ("confirmed_at", 1)],
        partialFilterExpression={"kind": "deposit", "status": "confirmed"},
    )
    await db.market_bets.create_index([("user_id", 1), ("created_at", -1)])
    await db.market_bets.create_index([("user_id", 1), ("status", 1), ("created_at", -1)])
    await db.market_bets.create_index([("market_id", 1), ("status", 1)])
    await db.market_bets.create_index(
        [("slip_group_id", 1), ("user_id", 1)],
        sparse=True,
    )
    await db.market_bets.create_index("created_at")
    await db.markets.create_index("created_at")
    await db.markets.create_index([("status", 1), ("created_at", -1)])
    await db.markets.create_index(
        [("source", 1), ("auto_resolve", 1), ("status", 1)],
    )
    for legacy in ("isports_match_id_1_bet_kind_1_line_1",):
        try:
            await db.markets.drop_index(legacy)
            log.info("Dropped legacy markets index %s", legacy)
        except Exception:
            pass
    await _create_index_migrate(
        db.markets,
        [("isports_match_id", 1), ("bet_kind", 1), ("line", 1)],
        index_name="isports_match_bet_line_v2",
        unique=True,
        partialFilterExpression={
            "source": "isports",
            "bet_kind": {
                "$in": [
                    "match_winner",
                    "match_home",
                    "goals_over",
                    "corners_over",
                    "btts",
                    "home_scores",
                    "away_scores",
                ]
            },
        },
    )
    await _create_index_migrate(
        db.markets,
        [("isports_match_id", 1), ("isports_player_id", 1)],
        index_name="isports_match_player_v1",
        unique=True,
        partialFilterExpression={
            "source": "isports",
            "bet_kind": "player_scores",
        },
    )
    await db.markets.create_index(
        [("source", 1), ("auto_resolve", 1), ("status", 1), ("resolve_after", 1)]
    )
    await db.isports_schedule_cache.create_index("date", unique=True)
    await db.isports_auto_sessions.create_index("expires_at", expireAfterSeconds=0)
    await db.presets.create_index("created_at")
    await db.blik_deposits.create_index("upload_token", unique=True)
    await db.blik_deposits.create_index([("user_id", 1), ("created_at", -1)])
    await db.blik_deposits.create_index([("status", 1), ("created_at", -1)])
    await db.blik_deposits.create_index("matched_withdraw_id", sparse=True)
    await db.blik_deposits.create_index(
        [("status", 1), ("flow", 1), ("created_at", -1)],
    )
    await db.blik_withdrawals.create_index([("status", 1), ("amount_pln", 1), ("created_at", 1)])
    await db.blik_withdrawals.create_index([("user_id", 1), ("created_at", -1)])
    await db.blik_withdrawals.create_index("status")
    await db.blackjack_sessions.create_index(
        [("user_id", 1), ("status", 1)],
        partialFilterExpression={"status": "playing"},
    )


async def close_db() -> None:
    global _client, _db, _connected_db_name
    if _client is not None:
        _client.close()
    _client = None
    _db = None
    _connected_db_name = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("DB not initialised")
    return _db


def connected_database_name() -> str:
    if _connected_db_name is None:
        raise RuntimeError("DB not initialised")
    return _connected_db_name


def peer_database_name() -> str | None:
    """Opposite env database: dev <-> prod. None if current DB is neither."""
    name = connected_database_name()
    if name == "dev":
        return "prod"
    if name == "prod":
        return "dev"
    return None


def get_peer_db() -> AsyncIOMotorDatabase:
    peer = peer_database_name()
    if peer is None:
        raise RuntimeError(f"No peer database for {connected_database_name()!r}")
    if _client is None:
        raise RuntimeError("DB not initialised")
    return _client.get_database(peer, codec_options=_CODEC)


def get_database(name: str) -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("DB not initialised")
    return _client.get_database(name, codec_options=_CODEC)


async def next_id_for(db: AsyncIOMotorDatabase, name: str) -> int:
    doc = await db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["seq"]


async def next_id(name: str) -> int:
    return await next_id_for(get_db(), name)
