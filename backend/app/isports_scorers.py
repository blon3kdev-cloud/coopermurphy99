"""Top league scorers → per-player 'will score' variants for iSports auto-import."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

from .auto_bets import _apply_house_edge
from .db import now
from .isports_api_client import fetch_top_scorers
from .top_sports_entities import is_top_football_player, same_team, top_football_player_profile

log = logging.getLogger(__name__)

TOP_PLAYERS_PER_TEAM = 3
_SCORER_CACHE_TTL = timedelta(hours=12)
_scorer_rows_cache: dict[str, tuple[datetime, list[dict]]] = {}


def _team_matches(
    player_team: str,
    schedule_team: str,
    *,
    schedule_team_id: str = "",
    player_team_id: str = "",
) -> bool:
    if schedule_team_id and player_team_id and schedule_team_id == player_team_id:
        return True
    return same_team(player_team, schedule_team, "football")


def _players_for_team(
    rows: list[dict],
    team_name: str,
    *,
    team_id: str = "",
) -> list[dict]:
    picked: list[dict] = []
    for row in rows:
        if not _team_matches(
            str(row.get("teamName", "")),
            team_name,
            schedule_team_id=team_id,
            player_team_id=str(row.get("teamId", "")),
        ):
            continue
        goals = int(row.get("goalsCount") or 0)
        matches = int(row.get("matchNum") or 0)
        picked.append(
            {
                "playerId": str(row.get("playerId", "")),
                "playerName": str(row.get("playerName", "")).strip(),
                "teamName": str(row.get("teamName", "")),
                "goalsCount": goals,
                "matchNum": matches,
            }
        )
    picked.sort(key=lambda p: (-p["goalsCount"], -p["matchNum"], p["playerName"]))
    out: list[dict] = []
    seen: set[str] = set()
    for p in picked:
        pid = p["playerId"]
        if not pid or pid in seen or not p["playerName"]:
            continue
        seen.add(pid)
        out.append(p)
        if len(out) >= TOP_PLAYERS_PER_TEAM:
            break
    return out


def _odds_player_scores(goals_count: int, match_num: int) -> tuple[float, float]:
    """Estimate yes/no decimal odds from season scoring rate (no per-player odds API)."""
    rate = goals_count / max(match_num, 1)
    prob_yes = min(0.55, max(0.1, rate * 0.75 + 0.08))
    yes_dec = max(1.05, 1.0 / prob_yes)
    no_dec = max(1.05, 1.0 / (1.0 - prob_yes))
    return _apply_house_edge(yes_dec, no_dec)


def _player_variant(
    *,
    match_id: str,
    home: str,
    away: str,
    player: dict,
    team_side: str,
) -> dict[str, Any]:
    pid = player["playerId"]
    name = player["playerName"]
    yes_odds, no_odds = _odds_player_scores(player["goalsCount"], player["matchNum"])
    team_label = home if team_side == "home" else away
    profile = top_football_player_profile(name)
    is_top = profile is not None
    variant: dict[str, Any] = {
        "key": f"player_score_{pid}",
        "label": f"{home} - {away}: {name} scores",
        "yesLabel": "Yes",
        "noLabel": "No",
        "yesOdds": round(yes_odds, 4),
        "noOdds": round(no_odds, 4),
        "betKind": "player_scores",
        "line": None,
        "isMain": False,
        "category": "player_scorer",
        "teamSide": team_side,
        "teamName": team_label,
        "playerId": pid,
        "playerName": name,
        "seasonGoals": player["goalsCount"],
        "isTopPlayer": is_top,
    }
    if profile:
        variant["topPlayer"] = profile
    return variant


async def _load_scorer_rows(league_id: str, season: Optional[str]) -> list[dict]:
    cache_key = f"{league_id}:{season or ''}"
    cached = _scorer_rows_cache.get(cache_key)
    if cached is not None:
        fetched_at, rows = cached
        if now() - fetched_at < _SCORER_CACHE_TTL:
            return list(rows)
    rows = await fetch_top_scorers(league_id, season)
    _scorer_rows_cache[cache_key] = (now(), list(rows))
    return rows


async def build_player_scorer_variants(match: dict) -> list[dict]:
    league_id = str(match.get("leagueId") or "").strip()
    if not league_id:
        log.warning("scorers skipped: no leagueId on match %s", match.get("matchId"))
        return []
    season = match.get("season")
    season_s = str(season).strip() if season else None
    try:
        rows = await _load_scorer_rows(league_id, season_s)
    except Exception as exc:
        log.warning("topscorer API failed league=%s: %s", league_id, exc)
        return []
    if not rows:
        log.info("topscorer API returned no rows for league=%s", league_id)
        return []

    home = str(match.get("homeName", ""))
    away = str(match.get("awayName", ""))
    home_id = str(match.get("homeId", ""))
    away_id = str(match.get("awayId", ""))
    mid = str(match.get("matchId", ""))
    variants: list[dict] = []
    for side, team, tid in (("home", home, home_id), ("away", away, away_id)):
        for player in _players_for_team(rows, team, team_id=tid):
            variants.append(
                _player_variant(
                    match_id=mid,
                    home=home,
                    away=away,
                    player=player,
                    team_side=side,
                )
            )
    if not variants:
        log.info(
            "no scorers matched for %s vs %s (league=%s, topscorer rows=%d)",
            home,
            away,
            league_id,
            len(rows),
        )
    return variants
