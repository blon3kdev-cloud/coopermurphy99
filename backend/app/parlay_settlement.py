"""Settle multi-leg parlay slips (market + crypto) after all legs are resolved."""
from __future__ import annotations

from decimal import Decimal

from .db import get_db
from .rewards_service import record_vip_activity


async def _collect_group_legs(db, slip_group_id: int, user_id: int) -> list[dict]:
    legs: list[dict] = []
    for coll in ("market_bets", "crypto_bets"):
        cursor = db[coll].find({"slip_group_id": slip_group_id, "user_id": user_id})
        async for b in cursor:
            legs.append(b)
    return legs


async def try_finalize_parlay(slip_group_id: int, user_id: int) -> None:
    """Credit combined payout once every leg in the group has settled and all won."""
    db = get_db()
    legs = await _collect_group_legs(db, slip_group_id, user_id)
    if len(legs) < 2:
        return

    if any(b.get("slip_paid") for b in legs):
        return

    statuses = [b["status"] for b in legs]
    if any(s == "pending" for s in statuses):
        return

    if any(s == "lost" for s in statuses):
        return

    if not all(s in ("won", "cashback") for s in statuses):
        return

    stake = legs[0].get("slip_stake_pln") or legs[0]["stake_pln"]
    combined = Decimal("1")
    for b in legs:
        combined *= b["odds"]

    payout = legs[0].get("slip_potential_win")
    if payout is None:
        payout = (stake * combined).quantize(Decimal("0.01"))
    else:
        payout = Decimal(str(payout))

    await db.users.update_one({"id": user_id}, {"$inc": {"balance_pln": payout}})
    await record_vip_activity(user_id, Decimal(0), payout)

    for coll in ("market_bets", "crypto_bets"):
        await db[coll].update_many(
            {"slip_group_id": slip_group_id, "user_id": user_id},
            {"$set": {"slip_paid": True}},
        )
