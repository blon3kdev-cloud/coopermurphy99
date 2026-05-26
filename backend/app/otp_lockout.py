"""OTP verify failure tracking — lockout after repeated bad attempts."""
from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException
from pymongo import ReturnDocument

from .db import get_db, now

OTP_FAIL_MAX = 10
OTP_LOCKOUT_SEC = 900


def _lockout_id(provider: str, client_key: str) -> str:
    return f"{provider}:{client_key}"


async def assert_otp_not_locked(provider: str, client_key: str) -> None:
    doc = await get_db().otp_lockouts.find_one(
        {"_id": _lockout_id(provider, client_key)},
    )
    if doc is None:
        return
    locked_until = doc.get("locked_until")
    if locked_until is not None and locked_until > now():
        raise HTTPException(status_code=429, detail="otp_locked")


async def record_otp_failure(provider: str, client_key: str) -> None:
    db = get_db()
    doc_id = _lockout_id(provider, client_key)
    doc = await db.otp_lockouts.find_one_and_update(
        {"_id": doc_id},
        {"$inc": {"failures": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    failures = int(doc.get("failures", 1))
    if failures >= OTP_FAIL_MAX:
        await db.otp_lockouts.update_one(
            {"_id": doc_id},
            {
                "$set": {
                    "locked_until": now() + timedelta(seconds=OTP_LOCKOUT_SEC),
                    "failures": 0,
                }
            },
        )


async def clear_otp_failures(provider: str, client_key: str) -> None:
    await get_db().otp_lockouts.delete_one({"_id": _lockout_id(provider, client_key)})
