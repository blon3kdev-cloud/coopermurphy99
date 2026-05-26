"""Singleton admin flags — BLIK mode, site maintenance, daily Discord codes."""
from __future__ import annotations

import time

from ..config import get_settings
from ..db import get_db, now

_SETTINGS_ID = "global"
_FLAGS_CACHE_TTL_SEC = 2.0
_flags_cache: tuple[float, dict] | None = None


def _invalidate_flags_cache() -> None:
    global _flags_cache
    _flags_cache = None


def _read_blik_active(doc: dict | None) -> bool:
    if not doc:
        return False
    if "blik_active" in doc:
        return bool(doc["blik_active"])
    # legacy fields from earlier build
    return bool(doc.get("blik_fallback_active") or doc.get("betclic_active"))


def _read_site_unavailable(doc: dict | None) -> bool:
    if not doc:
        return False
    return bool(doc.get("site_unavailable"))


def _flags_from_doc(doc: dict | None) -> dict:
    return {
        "blikActive": _read_blik_active(doc),
        "siteUnavailable": _read_site_unavailable(doc),
    }


async def get_admin_flags() -> dict:
    global _flags_cache
    cached = _flags_cache
    if cached is not None and time.monotonic() - cached[0] < _FLAGS_CACHE_TTL_SEC:
        return dict(cached[1])
    doc = await get_db().admin_settings.find_one({"_id": _SETTINGS_ID})
    flags = _flags_from_doc(doc)
    _flags_cache = (time.monotonic(), flags)
    return flags


async def set_blik_active(value: bool) -> dict:
    await get_db().admin_settings.update_one(
        {"_id": _SETTINGS_ID},
        {
            "$set": {
                "blik_active": value,
                "updated_at": now(),
            },
            "$unset": {"betclic_active": "", "blik_fallback_active": ""},
            "$setOnInsert": {"_id": _SETTINGS_ID},
        },
        upsert=True,
    )
    _invalidate_flags_cache()
    return await get_admin_flags()


async def set_site_unavailable(value: bool) -> dict:
    await get_db().admin_settings.update_one(
        {"_id": _SETTINGS_ID},
        {
            "$set": {
                "site_unavailable": value,
                "updated_at": now(),
            },
            "$setOnInsert": {"_id": _SETTINGS_ID},
        },
        upsert=True,
    )
    _invalidate_flags_cache()
    return await get_admin_flags()


def _daily_amount_from_doc(doc: dict | None) -> float | None:
    if not doc or "daily_code_amount_pln" not in doc:
        return None
    return float(doc["daily_code_amount_pln"])


def _daily_max_uses_from_doc(doc: dict | None) -> int | None:
    if not doc or "daily_code_max_uses" not in doc:
        return None
    return int(doc["daily_code_max_uses"])


async def get_daily_code_config() -> dict:
    """PLN amount and global use cap for auto-posted Discord daily codes."""
    env = get_settings()
    doc = await get_db().admin_settings.find_one({"_id": _SETTINGS_ID})
    amount = _daily_amount_from_doc(doc)
    if amount is None:
        amount = float(env.daily_code_amount_pln)
    max_uses = _daily_max_uses_from_doc(doc)
    if max_uses is None:
        max_uses = int(env.daily_code_max_uses)
    return {"amountPln": amount, "maxUses": max_uses}


async def set_daily_code_config(amount_pln: float, max_uses: int) -> dict:
    if amount_pln <= 0:
        raise ValueError("amount must be positive")
    if max_uses < 1:
        raise ValueError("max uses must be at least 1")
    await get_db().admin_settings.update_one(
        {"_id": _SETTINGS_ID},
        {
            "$set": {
                "daily_code_amount_pln": float(amount_pln),
                "daily_code_max_uses": int(max_uses),
                "updated_at": now(),
            },
            "$setOnInsert": {"_id": _SETTINGS_ID},
        },
        upsert=True,
    )
    return await get_daily_code_config()
