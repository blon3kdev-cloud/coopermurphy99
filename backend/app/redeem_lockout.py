"""Failed promo-code redeem tracking — lockout after repeated guesses."""
from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException
from pymongo import ReturnDocument

from .db import get_db, now

REDEEM_FAIL_MAX = 8
REDEEM_LOCKOUT_SEC = 1800


def _lockout_id(user_id: int, client_key: str) -> str:
    return f"{user_id}:{client_key}"


async def assert_redeem_not_locked(user_id: int, client_key: str) -> None:
    doc = await get_db().redeem_lockouts.find_one(
        {"_id": _lockout_id(user_id, client_key)},
    )
    if doc is None:
        return
    locked_until = doc.get("locked_until")
    if locked_until is not None and locked_until > now():
        raise HTTPException(status_code=429, detail="redeem_locked")


async def record_redeem_failure(user_id: int, client_key: str) -> None:
    db = get_db()
    doc_id = _lockout_id(user_id, client_key)
    doc = await db.redeem_lockouts.find_one_and_update(
        {"_id": doc_id},
        {"$inc": {"failures": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    failures = int(doc.get("failures", 1))
    if failures >= REDEEM_FAIL_MAX:
        await db.redeem_lockouts.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "locked_until": now() + timedelta(seconds=REDEEM_LOCKOUT_SEC),
                    "failures": 0,
                }
            },
        )


async def clear_redeem_failures(user_id: int, client_key: str) -> None:
    await get_db().redeem_lockouts.delete_one({"_id": _lockout_id(user_id, client_key)})
