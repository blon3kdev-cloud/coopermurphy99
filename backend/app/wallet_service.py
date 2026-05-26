"""Wallet withdraw balance holds — atomic debit on request, refund on cancel."""
from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException

from .db import get_db


async def hold_withdraw_balance(user_id: int, amount: Decimal) -> None:
    """Atomically debit balance when opening a pending withdraw."""
    updated = await get_db().users.find_one_and_update(
        {"id": user_id, "balance_pln": {"$gte": amount}},
        {"$inc": {"balance_pln": -amount}},
    )
    if not updated:
        raise HTTPException(status_code=400, detail="insufficient_balance")


async def release_withdraw_hold(user_id: int, amount: Decimal) -> None:
    """Refund held funds when a pending withdraw is cancelled or rejected."""
    await get_db().users.update_one(
        {"id": user_id},
        {"$inc": {"balance_pln": amount}},
    )
