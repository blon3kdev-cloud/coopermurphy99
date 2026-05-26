"""Mirror admin presets and bets to the opposite MongoDB env (dev <-> prod)."""
from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from .db import get_peer_db, next_id_for, now, peer_database_name
from .preset_matching import (
    _norm,
    apply_preset_to_eligible_markets,
    union_preset_names,
)

log = logging.getLogger(__name__)


def _peer_available() -> bool:
    return peer_database_name() is not None


async def _find_preset(
    db: AsyncIOMotorDatabase,
    preset_name: str,
    names: list[str],
) -> dict | None:
    name_key = _norm(preset_name)
    code_keys = {_norm(n) for n in names if str(n).strip()}
    async for row in db.presets.find({}):
        if _norm(row.get("name") or "") == name_key:
            return row
        for alias in (row.get("payload") or {}).get("names") or []:
            if _norm(alias) in code_keys:
                return row
    return None


async def upsert_preset(
    db: AsyncIOMotorDatabase,
    *,
    preset_name: str,
    payload: dict,
    refresh_existing: bool = False,
) -> dict[str, Any]:
    names = list(payload.get("names") or [])
    image_url = str(payload.get("imageUrl") or "")
    existing = await _find_preset(db, preset_name, names)

    match_names = names
    if existing and refresh_existing:
        old_payload = existing.get("payload") or {}
        match_names = union_preset_names(
            names,
            old_payload.get("names"),
            preset_name,
            existing.get("name"),
        )

    if existing:
        await db.presets.update_one(
            {"id": existing["id"]},
            {"$set": {"name": preset_name, "payload": payload}},
        )
        preset_id = existing["id"]
        action = "updated"
    else:
        preset_id = await next_id_for(db, "presets")
        await db.presets.insert_one(
            {
                "id": preset_id,
                "name": preset_name,
                "payload": payload,
                "created_at": now(),
            }
        )
        action = "created"

    applied = await apply_preset_to_eligible_markets(
        image_url,
        match_names,
        refresh_existing=refresh_existing,
        db=db,
    )
    return {"id": preset_id, "action": action, "appliedCount": len(applied)}


async def delete_preset_in_db(
    db: AsyncIOMotorDatabase,
    *,
    preset_name: str,
    names: list[str],
) -> bool:
    row = await _find_preset(db, preset_name, names)
    if not row:
        return False
    await db.presets.delete_one({"id": row["id"]})
    return True


async def upsert_market(db: AsyncIOMotorDatabase, doc: dict) -> str:
    market_id = doc["id"]
    existing = await db.markets.find_one({"id": market_id})
    payload = {k: v for k, v in doc.items() if k != "_id"}
    if existing:
        await db.markets.update_one({"id": market_id}, {"$set": payload})
        return "updated"
    await db.markets.insert_one(payload)
    return "created"


async def patch_market(db: AsyncIOMotorDatabase, market_id: str, patch: dict) -> str:
    existing = await db.markets.find_one({"id": market_id})
    if existing:
        await db.markets.update_one({"id": market_id}, {"$set": patch})
        return "updated"
    merged = {"id": market_id, "status": "active", "outcome": None, "created_at": now(), **patch}
    await db.markets.insert_one(merged)
    return "created"


async def mirror_preset_upsert(
    *,
    preset_name: str,
    payload: dict,
    refresh_existing: bool = False,
) -> None:
    if not _peer_available():
        return
    peer = get_peer_db()
    result = await upsert_preset(
        peer,
        preset_name=preset_name,
        payload=payload,
        refresh_existing=refresh_existing,
    )
    log.info(
        "Mirrored preset %r to %s (%s, applied=%s)",
        preset_name,
        peer_database_name(),
        result["action"],
        result["appliedCount"],
    )


async def mirror_preset_delete(*, preset_name: str, names: list[str]) -> None:
    if not _peer_available():
        return
    peer = get_peer_db()
    if await delete_preset_in_db(peer, preset_name=preset_name, names=names):
        log.info("Mirrored preset delete %r to %s", preset_name, peer_database_name())


async def mirror_market_upsert(doc: dict) -> None:
    if not _peer_available():
        return
    peer = get_peer_db()
    action = await upsert_market(peer, doc)
    log.info("Mirrored market %s to %s (%s)", doc.get("id"), peer_database_name(), action)


async def mirror_market_patch(market_id: str, patch: dict) -> None:
    if not _peer_available():
        return
    peer = get_peer_db()
    action = await patch_market(peer, market_id, patch)
    log.info("Mirrored market patch %s to %s (%s)", market_id, peer_database_name(), action)


async def mirror_to_peer(coro) -> None:
    """Run a peer mirror; log and swallow errors so admin requests still succeed."""
    if not _peer_available():
        return
    try:
        await coro
    except Exception:
        log.exception("Failed to mirror to %s", peer_database_name())


async def merge_presets(source: AsyncIOMotorDatabase, target: AsyncIOMotorDatabase) -> dict:
    created = updated = 0
    async for row in source.presets.find({}).sort("created_at", 1):
        payload = row.get("payload") or {}
        names = list(payload.get("names") or [])
        if not names or not payload.get("imageUrl"):
            continue
        preset_name = str(row.get("name") or names[0]).strip() or names[0]
        existing = await _find_preset(target, preset_name, names)
        result = await upsert_preset(
            target,
            preset_name=preset_name,
            payload=payload,
            refresh_existing=bool(existing),
        )
        if result["action"] == "created":
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated}


async def merge_markets(source: AsyncIOMotorDatabase, target: AsyncIOMotorDatabase) -> dict:
    created = updated = 0
    async for row in source.markets.find({}).sort("created_at", 1):
        doc = {k: v for k, v in row.items() if k != "_id"}
        action = await upsert_market(target, doc)
        if action == "created":
            created += 1
        else:
            updated += 1
    return {"created": created, "updated": updated}
