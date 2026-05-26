"""Settle pending market bets (win / loss / cashback)."""
from __future__ import annotations

from typing import Literal

from decimal import Decimal

from .db import get_db
from .parlay_settlement import try_finalize_parlay
from .rewards_service import record_vip_activity

Outcome = Literal["yes", "no", "cashback", "draw"]


async def settle_pending_market_bets(market_id: str, outcome: Outcome) -> int:
    """Settle all pending placements on a market. Returns count settled."""
    db = get_db()
    count = 0
    cursor = db.market_bets.find({"market_id": market_id, "status": "pending"})
    async for b in cursor:
        count += 1
        gid = b.get("slip_group_id")
        stake = b.get("slip_stake_pln") or b["stake_pln"]

        if outcome == "cashback":
            await db.market_bets.update_one(
                {"id": b["id"]},
                {"$set": {"status": "cashback"}},
            )
            if gid is None:
                await db.users.update_one(
                    {"id": b["user_id"]},
                    {"$inc": {"balance_pln": stake}},
                )
            else:
                await try_finalize_parlay(gid, b["user_id"])
            continue

        won = outcome != "draw" and b["side"] == outcome
        await db.market_bets.update_one(
            {"id": b["id"]},
            {"$set": {"status": "won" if won else "lost"}},
        )

        if gid is not None:
            await try_finalize_parlay(gid, b["user_id"])
            continue

        if won:
            payout = stake * b["odds"]
            await db.users.update_one(
                {"id": b["user_id"]},
                {"$inc": {"balance_pln": payout}},
            )
            await record_vip_activity(b["user_id"], Decimal(0), Decimal(str(payout)))
    return count
