"""Daily auto-resolve iSports markets from finished match scores."""
from __future__ import annotations

import logging
from typing import Optional

from datetime import datetime, timezone

from .db import get_db
from .market_utils import market_bet_start_at
from .isports_queue import (
    enqueue_liveanimation_by_match_ids,
    enqueue_player_goals_by_match_ids,
    enqueue_schedule_by_match_ids,
)
from .market_settlement import Outcome, settle_pending_market_bets

log = logging.getLogger(__name__)

FOOTBALL_CANCELLED_STATUSES = frozenset({-10, -12, -13, -14})
BASKETBALL_CANCELLED_STATUSES = frozenset({-3, -4, -5})
FINISHED_STATUS = -1


def _int(val: object, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _float_line(val: object) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def compute_outcome(
    *,
    bet_kind: str,
    line: Optional[float],
    home_score: int,
    away_score: int,
    home_corners: int,
    away_corners: int,
) -> Outcome:
    total_goals = home_score + away_score
    total_corners = home_corners + away_corners

    if bet_kind in ("match_winner", "match_home"):
        if home_score > away_score:
            return "yes"
        if home_score < away_score:
            return "no"
        return "draw"

    if bet_kind == "home_scores":
        return "yes" if home_score > 0 else "no"

    if bet_kind == "away_scores":
        return "yes" if away_score > 0 else "no"

    if bet_kind == "goals_over":
        ln = line or 0.0
        if total_goals > ln:
            return "yes"
        if total_goals < ln:
            return "no"
        return "cashback"

    if bet_kind == "corners_over":
        ln = line or 0.0
        if total_corners > ln:
            return "yes"
        if total_corners < ln:
            return "no"
        return "cashback"

    if bet_kind == "btts":
        if home_score > 0 and away_score > 0:
            return "yes"
        return "no"

    return "cashback"


def _outcome_for_market(
    market: dict,
    sched: dict,
    *,
    live_map: dict[str, dict],
    player_goals_map: dict[str, dict[str, int]],
) -> Optional[Outcome]:
    """Return outcome if match is finished/cancelled; None if still in play or unknown."""
    status = _int(sched.get("status"), 0)
    bet_kind = str(market.get("bet_kind", ""))
    odds_sport = str(market.get("odds_sport", "football"))
    cancelled = (
        BASKETBALL_CANCELLED_STATUSES
        if odds_sport == "basketball"
        else FOOTBALL_CANCELLED_STATUSES
    )
    if status in cancelled:
        return "cashback"
    if status != FINISHED_STATUS:
        return None

    mid = str(market.get("isports_match_id", ""))
    if bet_kind == "player_scores":
        pid = str(market.get("isports_player_id", ""))
        goals_map = player_goals_map.get(mid) or {}
        if not goals_map and pid:
            return None
        return "yes" if goals_map.get(pid, 0) > 0 else "no"

    home_score = _int(sched.get("homeScore"))
    away_score = _int(sched.get("awayScore"))
    home_corners = _int(sched.get("homeCorner"))
    away_corners = _int(sched.get("awayCorner"))
    if home_corners == 0 and away_corners == 0:
        live = live_map.get(mid)
        if live:
            home_corners = _int(live.get("homeCorner"))
            away_corners = _int(live.get("awayCorner"))
    return compute_outcome(
        bet_kind=bet_kind,
        line=_float_line(market.get("line")),
        home_score=home_score,
        away_score=away_score,
        home_corners=home_corners,
        away_corners=away_corners,
    )


def market_event_has_ended(market: dict, *, now: datetime | None = None) -> bool:
    """True when kickoff is in the past (UTC). Missing date → not ended."""
    start = market_bet_start_at(market)
    if start is None:
        return False
    ref = now or datetime.now(timezone.utc)
    return start <= ref


async def preview_isports_auto_resolve() -> dict:
    """Active auto-resolve iSports markets grouped by whether event time has passed."""
    db = get_db()
    ref = datetime.now(timezone.utc)
    markets = await db.markets.find(
        {
            "source": "isports",
            "auto_resolve": True,
            "status": "active",
        }
    ).to_list(5000)
    ended = [m for m in markets if market_event_has_ended(m, now=ref)]
    upcoming = [m for m in markets if not market_event_has_ended(m, now=ref)]
    return {
        "totalActive": len(markets),
        "endedCount": len(ended),
        "upcomingCount": len(upcoming),
        "ended": [
            {"id": m["id"], "title": m.get("title", ""), "eventDate": m.get("event_date")}
            for m in ended
        ],
    }


async def resolve_isports_markets(*, only_event_ended: bool = False) -> dict:
    """Resolve active iSports markets whose matches have ended (per iSports status)."""
    db = get_db()
    ref = datetime.now(timezone.utc)
    markets = await db.markets.find(
        {
            "source": "isports",
            "auto_resolve": True,
            "status": "active",
        }
    ).to_list(5000)
    if only_event_ended:
        markets = [m for m in markets if market_event_has_ended(m, now=ref)]
    logs: list[dict] = []
    if not markets:
        log.info("isports resolve: no active markets")
        return {
            "resolved": 0,
            "checked": 0,
            "skippedLive": 0,
            "skippedNoSchedule": 0,
            "logs": logs,
        }

    football_ids = list(
        {
            str(m["isports_match_id"])
            for m in markets
            if m.get("isports_match_id") and str(m.get("odds_sport", "football")) != "basketball"
        }
    )
    basketball_ids = list(
        {
            str(m["isports_match_id"])
            for m in markets
            if m.get("isports_match_id") and str(m.get("odds_sport", "")) == "basketball"
        }
    )

    schedule_map: dict[str, dict] = {}
    if football_ids:
        schedule_map.update(await enqueue_schedule_by_match_ids(football_ids, sport="football"))
    if basketball_ids:
        schedule_map.update(await enqueue_schedule_by_match_ids(basketball_ids, sport="basketball"))

    live_map = await enqueue_liveanimation_by_match_ids(football_ids)
    player_match_ids = list(
        {
            str(m["isports_match_id"])
            for m in markets
            if m.get("isports_match_id") and m.get("bet_kind") == "player_scores"
        }
    )
    player_goals_map = await enqueue_player_goals_by_match_ids(player_match_ids)

    resolved_count = 0
    skipped_live = 0
    skipped_no_schedule = 0
    title_by_id = {m["id"]: str(m.get("title", "")) for m in markets}

    for market in markets:
        mid = str(market.get("isports_match_id", ""))
        market_id = market["id"]
        title = title_by_id.get(market_id, "")
        sched = schedule_map.get(mid) or live_map.get(mid)
        if not sched:
            skipped_no_schedule += 1
            logs.append(
                {
                    "marketId": market_id,
                    "title": title,
                    "level": "warn",
                    "message": "Brak danych meczu w iSports",
                }
            )
            continue

        outcome = _outcome_for_market(
            market,
            sched,
            live_map=live_map,
            player_goals_map=player_goals_map,
        )
        if outcome is None:
            skipped_live += 1
            logs.append(
                {
                    "marketId": market_id,
                    "title": title,
                    "level": "info",
                    "message": "Mecz jeszcze trwa lub brak wyniku",
                }
            )
            continue

        await db.markets.update_one(
            {"id": market_id},
            {"$set": {"status": "resolved", "outcome": outcome}},
        )
        await settle_pending_market_bets(market_id, outcome)
        resolved_count += 1
        logs.append(
            {
                "marketId": market_id,
                "title": title,
                "level": "success",
                "message": f"Rozstrzygnięto → {outcome}",
                "outcome": outcome,
            }
        )
        log.info("isports resolved %s -> %s", market_id, outcome)

    log.info(
        "isports resolve done: %d resolved, %d still active (not finished), %d markets checked",
        resolved_count,
        skipped_live,
        len(markets),
    )
    return {
        "resolved": resolved_count,
        "checked": len(markets),
        "skippedLive": skipped_live,
        "skippedNoSchedule": skipped_no_schedule,
        "logs": logs,
    }
