"""Withdrawal playthrough — deposited / credited funds must be wagered 5× before cash-out."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import HTTPException

from .db import get_db

PLAYTHROUGH_MULTIPLIER = 5


def playthrough_status(user: dict | None) -> dict[str, Any]:
    if not user:
        return {
            "base": Decimal(0),
            "wagered": Decimal(0),
            "required": Decimal(0),
            "remaining": Decimal(0),
            "satisfied": True,
            "multiplier": PLAYTHROUGH_MULTIPLIER,
        }
    base = Decimal(str(user.get("playthrough_base_pln") or 0))
    wagered = Decimal(str(user.get("playthrough_wagered_pln") or 0))
    required = (base * PLAYTHROUGH_MULTIPLIER).quantize(Decimal("0.01"))
    remaining = max(Decimal(0), required - wagered).quantize(Decimal("0.01"))
    return {
        "base": base,
        "wagered": wagered,
        "required": required,
        "remaining": remaining,
        "satisfied": remaining <= 0,
        "multiplier": PLAYTHROUGH_MULTIPLIER,
    }


async def record_playthrough_credit(user_id: int, amount: Decimal) -> None:
    """Increase locked credit base (deposits, promo grants, referral bonuses, etc.)."""
    amount = Decimal(str(amount or 0))
    if amount <= 0:
        return
    await get_db().users.update_one(
        {"id": user_id},
        {"$inc": {"playthrough_base_pln": amount}},
    )


async def record_playthrough_wager(user_id: int, stake: Decimal) -> None:
    """Count stake volume toward the playthrough requirement."""
    stake = Decimal(str(stake or 0))
    if stake <= 0:
        return
    await get_db().users.update_one(
        {"id": user_id},
        {"$inc": {"playthrough_wagered_pln": stake}},
    )


async def ensure_withdraw_allowed(user_id: int) -> None:
    user = await get_db().users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    st = playthrough_status(user)
    if st["satisfied"]:
        return
    raise HTTPException(
        status_code=403,
        detail={
            "code": "withdraw_playthrough_required",
            "remainingWagerPln": float(st["remaining"]),
            "requiredTotalWagerPln": float(st["required"]),
            "wageredPln": float(st["wagered"]),
            "creditBasePln": float(st["base"]),
            "multiplier": PLAYTHROUGH_MULTIPLIER,
        },
    )
