"""Create and redeem promo codes (multi-use)."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from fastapi import HTTPException
from pymongo import ReturnDocument

from .db import as_utc, get_db, next_id, now
from .redeem_lockout import clear_redeem_failures, record_redeem_failure
from .security import (
    generate_daily_reward_code,
    generate_nick_reward_code,
    generate_redeem_code,
)

CodeKind = Literal["admin", "daily", "nick"]


def _generate_code_for_kind(kind: CodeKind) -> str:
    if kind == "daily":
        return generate_daily_reward_code()
    if kind == "nick":
        return generate_nick_reward_code()
    return generate_redeem_code()


def _effective_max_uses(row: dict) -> int:
    if row.get("max_uses") is not None:
        return int(row["max_uses"])
    return 1


def _effective_uses_count(row: dict) -> int:
    if row.get("uses_count") is not None:
        return int(row["uses_count"])
    return 1 if row.get("used_at") else 0


def code_is_exhausted(row: dict) -> bool:
    return _effective_uses_count(row) >= _effective_max_uses(row)


async def create_redeem_code(
    amount_pln: Decimal,
    max_uses: int,
    *,
    kind: CodeKind = "admin",
    issued_to: Optional[int] = None,
    label: Optional[str] = None,
    code: Optional[str] = None,
    expires_at: Optional[datetime] = None,
) -> dict[str, Any]:
    if max_uses < 1:
        raise ValueError("max_uses must be at least 1")
    if amount_pln <= 0:
        raise ValueError("amount must be positive")

    db = get_db()
    for _ in range(20):
        candidate = (code or _generate_code_for_kind(kind)).strip().upper()
        exists = await db.redeem_codes.find_one({"code": candidate}, {"_id": 1})
        if not exists:
            break
        code = None
    else:
        raise HTTPException(status_code=500, detail="cannot allocate code")

    doc = {
        "id": await next_id("redeem_codes"),
        "code": candidate,
        "amount_pln": amount_pln,
        "max_uses": max_uses,
        "uses_count": 0,
        "kind": kind,
        "label": label or kind,
        "issued_to": issued_to,
        "redeemed_user_ids": [],
        "used_by": None,
        "used_at": None,
        "created_at": now(),
        "expires_at": expires_at,
    }
    await db.redeem_codes.insert_one(doc)
    return doc


async def redeem_code(
    user: dict,
    code: str,
    *,
    client_key: str | None = None,
) -> dict:
    db = get_db()
    normalized = code.strip().upper()
    row = await db.redeem_codes.find_one({"code": normalized})
    if row is None:
        if client_key:
            await record_redeem_failure(user["id"], client_key)
        raise HTTPException(status_code=404, detail="invalid or used code")

    expires = row.get("expires_at")
    if expires is not None and now() >= as_utc(expires):
        if client_key:
            await record_redeem_failure(user["id"], client_key)
        raise HTTPException(status_code=404, detail="code expired")

    if row.get("issued_to") is not None and row["issued_to"] != user["id"]:
        if client_key:
            await record_redeem_failure(user["id"], client_key)
        raise HTTPException(status_code=404, detail="invalid or used code")

    max_uses = _effective_max_uses(row)
    uses = _effective_uses_count(row)
    if uses >= max_uses:
        if client_key:
            await record_redeem_failure(user["id"], client_key)
        raise HTTPException(status_code=404, detail="invalid or used code")

    redeemed_ids = row.get("redeemed_user_ids") or []
    if user["id"] in redeemed_ids:
        raise HTTPException(status_code=409, detail="already redeemed")

    filt: dict = {
        "code": normalized,
        "redeemed_user_ids": {"$nin": [user["id"]]},
    }
    if row.get("uses_count") is not None:
        filt["uses_count"] = {"$lt": max_uses}
    else:
        filt["used_at"] = None

    updated_row = await db.redeem_codes.find_one_and_update(
        filt,
        {
            "$inc": {"uses_count": 1},
            "$addToSet": {"redeemed_user_ids": user["id"]},
            "$set": {
                "used_by": user["id"],
                "used_at": now(),
                "max_uses": max_uses,
            },
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated_row is None:
        if user["id"] in (row.get("redeemed_user_ids") or []):
            raise HTTPException(status_code=409, detail="already redeemed")
        if client_key:
            await record_redeem_failure(user["id"], client_key)
        raise HTTPException(status_code=404, detail="invalid or used code")

    amount = Decimal(str(updated_row["amount_pln"]))
    updated_user = await db.users.find_one_and_update(
        {"id": user["id"]},
        {"$inc": {"balance_pln": amount, "playthrough_base_pln": amount}},
        return_document=ReturnDocument.AFTER,
    )
    if updated_user is None:
        raise HTTPException(status_code=404, detail="user not found")
    if client_key:
        await clear_redeem_failures(user["id"], client_key)
    return {
        "ok": True,
        "amount": float(amount),
        "balance": float(updated_user["balance_pln"]),
    }


def serialize_code_row(row: dict) -> dict:
    max_u = _effective_max_uses(row)
    used = _effective_uses_count(row)
    amount = float(row["amount_pln"])
    return {
        "id": row.get("id") or row.get("code"),
        "code": row["code"],
        "amount": amount,
        "amountPln": amount,
        "maxUses": max_u,
        "usesCount": used,
        "remaining": max(0, max_u - used),
        "kind": row.get("kind") or "admin",
        "label": row.get("label") or row.get("kind") or "—",
        "status": "exhausted" if used >= max_u else "active",
        "createdAt": row["created_at"].strftime("%Y-%m-%d %H:%M"),
    }
