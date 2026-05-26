"""Refresh active iSports market odds on a schedule (main 1h, side 6h)."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

from .auto_bets import _apply_house_edge
from .db import get_db
from .isports_api_client import (
    fetch_basketball_odds_fulltime,
    fetch_both_score,
    fetch_corners_total,
    fetch_european_1x2,
    pick_basketball_moneyline,
    pick_btts_row,
    pick_corners_row,
    pick_goals_over_lines,
    pick_match_winner_odds,
    pick_over_under,
)
from .isports_bookmakers import get_bookmaker_pref
from .isports_queue import enqueue, enqueue_odds_main_by_match_ids, enqueue_schedule_by_match_ids
from .isports_scorers import _load_scorer_rows, _odds_player_scores, _team_matches

log = logging.getLogger(__name__)

MAIN_BET_KINDS = frozenset({"match_winner", "match_home"})


def _odds_changed(market: dict, new_yes: float, new_no: float) -> bool:
    try:
        yes = float(market.get("yes_odds", 0))
        no = float(market.get("no_odds", 0))
    except (TypeError, ValueError):
        return True
    return abs(yes - new_yes) > 0.001 or abs(no - new_no) > 0.001


async def _update_market_odds(market: dict, yes_odds: float, no_odds: float) -> bool:
    if yes_odds <= 1 or no_odds <= 1:
        return False
    if not _odds_changed(market, yes_odds, no_odds):
        return False
    db = get_db()
    await db.markets.update_one(
        {"id": market["id"]},
        {
            "$set": {
                "yes_odds": Decimal(str(round(yes_odds, 4))),
                "no_odds": Decimal(str(round(no_odds, 4))),
            }
        },
    )
    return True


async def _refresh_main_football(markets: list[dict]) -> int:
    by_match: dict[str, list[dict]] = {}
    for m in markets:
        if str(m.get("odds_sport", "football")) == "basketball":
            continue
        mid = str(m.get("isports_match_id", ""))
        if mid:
            by_match.setdefault(mid, []).append(m)
    if not by_match:
        return 0

    match_ids = list(by_match.keys())
    odds_main = await enqueue_odds_main_by_match_ids(match_ids)
    pref = get_bookmaker_pref()
    european_1x2: dict[str, tuple[float, float, float]] = {}
    if pref.eu_ids:
        for chunk_start in range(0, len(match_ids), 100):
            chunk = match_ids[chunk_start : chunk_start + 100]

            async def _eu_job(c: list[str] = chunk) -> dict[str, tuple[float, float, float]]:
                return await fetch_european_1x2(c)

            try:
                part = await enqueue(_eu_job)
                if isinstance(part, dict):
                    european_1x2.update(part)
            except Exception as exc:
                log.warning("isports odds refresh european 1x2: %s", exc)

    updated = 0
    europe_rows = odds_main.get("europeOdds") or []
    for mid, group in by_match.items():
        eu = pick_match_winner_odds(
            mid,
            european_1x2=european_1x2 or None,
            main_europe_rows=europe_rows,
        )
        if not eu:
            continue
        home_o, _draw_o, away_o = eu
        yes_odds, no_odds = _apply_house_edge(home_o, away_o)
        for market in group:
            if await _update_market_odds(market, yes_odds, no_odds):
                updated += 1
    return updated


async def _refresh_main_basketball(markets: list[dict]) -> int:
    nba = [m for m in markets if str(m.get("odds_sport", "")) == "basketball"]
    if not nba:
        return 0

    pref = get_bookmaker_pref()

    async def _job() -> dict[str, Any]:
        return await fetch_basketball_odds_fulltime()

    odds_data = await enqueue(_job)
    money_rows = odds_data.get("moneyLine") if isinstance(odds_data, dict) else []
    if not isinstance(money_rows, list):
        return 0

    updated = 0
    for market in nba:
        mid = str(market.get("isports_match_id", ""))
        pair = pick_basketball_moneyline(
            money_rows,
            mid,
            company_ids=pref.main_ids or pref.sub_market_main_ids,
        )
        if not pair:
            continue
        yes_odds, no_odds = _apply_house_edge(*pair)
        if await _update_market_odds(market, yes_odds, no_odds):
            updated += 1
    return updated


async def _refresh_side_football(markets: list[dict]) -> int:
    football = [m for m in markets if str(m.get("odds_sport", "football")) != "basketball"]
    if not football:
        return 0

    by_match: dict[str, list[dict]] = {}
    for m in football:
        mid = str(m.get("isports_match_id", ""))
        if mid:
            by_match.setdefault(mid, []).append(m)

    match_ids = list(by_match.keys())
    schedule_map = await enqueue_schedule_by_match_ids(match_ids, sport="football")
    odds_main = await enqueue_odds_main_by_match_ids(match_ids)

    corners_rows: list[dict] = []
    btts_rows: list[dict] = []
    for chunk_start in range(0, len(match_ids), 100):
        chunk = match_ids[chunk_start : chunk_start + 100]

        async def _corners_job(c: list[str] = chunk) -> list[dict]:
            return await fetch_corners_total(c)

        async def _btts_job(c: list[str] = chunk) -> list[dict]:
            return await fetch_both_score(c)

        try:
            corners_rows.extend(await enqueue(_corners_job))
        except Exception as exc:
            log.warning("isports side odds corners: %s", exc)
        try:
            btts_rows.extend(await enqueue(_btts_job))
        except Exception as exc:
            log.warning("isports side odds btts: %s", exc)

    updated = 0
    over_rows = odds_main.get("overUnder") or []

    for market in football:
        mid = str(market.get("isports_match_id", ""))
        bet_kind = str(market.get("bet_kind", ""))
        yes_odds: Optional[float] = None
        no_odds: Optional[float] = None

        if bet_kind == "player_scores":
            sched = schedule_map.get(mid)
            if not sched:
                continue
            league_id = str(sched.get("leagueId") or "").strip()
            if not league_id:
                continue
            season = sched.get("season")
            season_s = str(season).strip() if season else None
            try:
                rows = await _load_scorer_rows(league_id, season_s)
            except Exception as exc:
                log.warning("isports player odds refresh %s: %s", mid, exc)
                continue
            pid = str(market.get("isports_player_id", ""))
            pname = str(market.get("player_name", ""))
            home = str(sched.get("homeName", ""))
            away = str(sched.get("awayName", ""))
            home_id = str(sched.get("homeId", ""))
            away_id = str(sched.get("awayId", ""))
            player_row = None
            for side, team, tid in (("home", home, home_id), ("away", away, away_id)):
                for row in rows:
                    if str(row.get("playerId", "")) != pid:
                        continue
                    if _team_matches(
                        str(row.get("teamName", "")),
                        team,
                        schedule_team_id=tid,
                        player_team_id=str(row.get("teamId", "")),
                    ):
                        player_row = row
                        break
                if player_row:
                    break
            if not player_row and pname:
                for row in rows:
                    if str(row.get("playerId", "")) == pid or str(row.get("playerName", "")).strip() == pname:
                        player_row = row
                        break
            if not player_row:
                continue
            goals = int(player_row.get("goalsCount") or 0)
            matches = int(player_row.get("matchNum") or 0)
            yes_odds, no_odds = _odds_player_scores(goals, matches)

        elif bet_kind == "goals_over":
            line = market.get("line")
            if line is None:
                continue
            ln = float(line)
            for _line, over_o, under_o in pick_goals_over_lines(over_rows, mid):
                if abs(_line - ln) < 0.01:
                    yes_odds, no_odds = _apply_house_edge(over_o, under_o)
                    break
            if yes_odds is None:
                for _line, over_o, under_o in pick_over_under(over_rows, mid):
                    if abs(_line - ln) < 0.01:
                        yes_odds, no_odds = _apply_house_edge(over_o, under_o)
                        break

        elif bet_kind == "corners_over":
            line = market.get("line")
            if line is None:
                continue
            ln = float(line)
            row = pick_corners_row(corners_rows, mid)
            if row and abs(row[0] - ln) < 0.01:
                _l, over_o, under_o = row
                yes_odds, no_odds = _apply_house_edge(over_o, under_o)

        elif bet_kind == "btts":
            pair = pick_btts_row(btts_rows, mid)
            if pair:
                yes_odds, no_odds = _apply_house_edge(*pair)

        elif bet_kind == "home_scores":
            for _line, over_o, under_o in pick_over_under(over_rows, mid):
                if _line <= 0.6:
                    yes_odds, no_odds = _apply_house_edge(over_o, under_o)
                    break

        elif bet_kind == "away_scores":
            for _line, over_o, under_o in pick_over_under(over_rows, mid):
                if _line <= 0.6:
                    yes_odds, no_odds = _apply_house_edge(over_o, under_o)
                    break

        if yes_odds is not None and no_odds is not None:
            if await _update_market_odds(market, yes_odds, no_odds):
                updated += 1

    return updated


async def refresh_isports_odds(*, main: bool) -> int:
    """Update yes/no odds on active iSports markets. Returns count updated."""
    db = get_db()
    query: dict[str, Any] = {"source": "isports", "status": "active"}
    if main:
        query["bet_kind"] = {"$in": list(MAIN_BET_KINDS)}
    else:
        query["bet_kind"] = {"$nin": list(MAIN_BET_KINDS)}

    markets = await db.markets.find(query).to_list(5000)
    if not markets:
        log.info("isports odds refresh (%s): nothing to update", "main" if main else "side")
        return 0

    if main:
        n = await _refresh_main_football(markets) + await _refresh_main_basketball(markets)
    else:
        n = await _refresh_side_football(markets)

    log.info("isports odds refresh (%s): %d/%d markets updated", "main" if main else "side", n, len(markets))
    return n


async def refresh_main_odds() -> int:
    return await refresh_isports_odds(main=True)


async def refresh_side_odds() -> int:
    return await refresh_isports_odds(main=False)
