"""Aggregate bet count and stake volume per market."""
from __future__ import annotations

from decimal import Decimal

from .db import get_db


async def bet_stats_by_market(market_ids: list[str]) -> dict[str, dict]:
    if not market_ids:
        return {}
    db = get_db()
    stats: dict[str, dict] = {}
    cursor = db.market_bets.find({"market_id": {"$in": market_ids}})
    async for bet in cursor:
        mid = str(bet["market_id"])
        bucket = stats.setdefault(mid, {"bet_count": 0, "money": Decimal(0)})
        bucket["bet_count"] += 1
        stake = bet.get("stake_pln") or Decimal(0)
        if stake > 0:
            bucket["money"] += Decimal(str(stake))
            continue
        slip_id = bet.get("slip_group_id")
        slip_stake = bet.get("slip_stake_pln") or Decimal(0)
        if slip_id is None:
            continue
        counted = bucket.setdefault("_parlays", set())
        if slip_id in counted:
            continue
        counted.add(slip_id)
        bucket["money"] += Decimal(str(slip_stake))
    return stats
