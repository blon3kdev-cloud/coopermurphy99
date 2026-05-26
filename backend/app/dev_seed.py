"""Idempotent dev fixtures — dev login user only (development)."""
from __future__ import annotations

import logging
from decimal import Decimal

from .config import get_settings
from .db import get_db, next_id, now
from .security import generate_pass_key, hash_password

log = logging.getLogger(__name__)

_DEV_TELEGRAM = "dev-local-999"
_DEV_MARKET_IDS = ("dev-m1", "dev-m2", "dev-m3")


async def _purge_legacy_sample_bets() -> None:
    db = get_db()
    bet_result = await db.market_bets.delete_many({"market_id": {"$in": list(_DEV_MARKET_IDS)}})
    market_result = await db.markets.delete_many({"id": {"$in": list(_DEV_MARKET_IDS)}})
    if bet_result.deleted_count or market_result.deleted_count:
        log.info(
            "dev seed: removed legacy sample data (%d bets, %d markets)",
            bet_result.deleted_count,
            market_result.deleted_count,
        )


async def seed_dev_data() -> None:
    settings = get_settings()
    if not settings.is_development:
        return

    await _purge_legacy_sample_bets()

    db = get_db()
    row = await db.users.find_one({"username": settings.dev_username})
    if row is None:
        user_id = await next_id("users")
        await db.users.insert_one(
            {
                "id": user_id,
                "username": settings.dev_username,
                "password_hash": hash_password("dev-password-unused"),
                "pass_key_hash": hash_password(generate_pass_key()),
                "telegram_id": _DEV_TELEGRAM,
                "discord_id": None,
                "balance_pln": Decimal("5000"),
                "banned": False,
                "last_nick_reward_at": None,
                "referred_by_id": None,
                "vip_wagered_pln": Decimal("0"),
                "vip_won_pln": Decimal("0"),
                "playthrough_base_pln": Decimal("0"),
                "playthrough_wagered_pln": Decimal("0"),
                "vip_period_stats": {},
                "vip_rank_claimed_tiers": [],
                "vip_bonus_claims": {},
                "referral_claimed_tiers": [],
                "created_at": now(),
                "last_seen_at": now(),
            }
        )
        log.info("dev seed: created user %s (id=%s)", settings.dev_username, user_id)
    else:
        user_id = row["id"]
        bal = max(Decimal(str(row["balance_pln"])), Decimal("5000"))
        await db.users.update_one({"id": user_id}, {"$set": {"balance_pln": bal}})
