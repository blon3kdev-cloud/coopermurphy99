"""iSports auto-import sessions, variant catalog, and external market creation."""
from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException

from .safe_url import safe_image_url
from .auto_bets import (
    AUTO_BET_HOUSE_EDGE,
    _apply_house_edge,
    _created_admin_row,
    _preset_lookup,
    _resolve_image,
    _resolve_image_for_name,
)
from .db import get_db, now
from .isports_api_client import (
    IsportsNotConfiguredError,
    fetch_basketball_odds_fulltime,
    fetch_european_rows,
    fetch_odds_main,
    match_time_dt,
    pick_basketball_moneyline,
    pick_europe_from_rows,
    pick_europe_odds,
)
from .isports_bookmakers import all_main_company_ids, get_bookmaker_pref, iter_bookmaker_fallback_prefs
from .top_sports_entities import is_womens_team
from .isports_queue import load_schedule_until_enough
from .isports_scorers import build_player_scorer_variants
from .market_utils import format_event_date
from .top_sports_entities import is_top_football_match, is_top_nba_match

log = logging.getLogger(__name__)

SESSION_TTL = timedelta(hours=2)
RESOLVE_AFTER_FOOTBALL = timedelta(minutes=105)
RESOLVE_AFTER_BASKETBALL = timedelta(minutes=180)


def _norm_line(line: float) -> str:
    s = f"{line:g}"
    return s.replace(".", "_")


def _filter_upcoming_matches(
    rows: list[dict],
    *,
    predicate,
) -> list[dict]:
    now_ts = datetime.now(timezone.utc)
    out: list[dict] = []
    for row in rows:
        if int(row.get("status", -99)) != 0:
            continue
        home = str(row.get("homeName", ""))
        away = str(row.get("awayName", ""))
        if not home or not away:
            continue
        if is_womens_team(home) or is_womens_team(away):
            continue
        if not predicate(home, away, row):
            continue
        mt = match_time_dt(row)
        if mt is None or mt <= now_ts:
            continue
        out.append(row)
    out.sort(key=lambda r: int(r.get("matchTime") or 0))
    return out


def _filter_football_matches(rows: list[dict]) -> list[dict]:
    return _filter_upcoming_matches(
        rows,
        predicate=lambda h, a, r: is_top_football_match(h, a, r),
    )


def _filter_nba_matches(rows: list[dict]) -> list[dict]:
    return _filter_upcoming_matches(
        rows,
        predicate=lambda h, a, r: is_top_nba_match(h, a, r),
    )


def _schedule_filter(sport: str):
    if sport == "basketball":
        return _filter_nba_matches
    return _filter_football_matches


async def _existing_isports_match_ids(sport: str) -> set[str]:
    """Match IDs that already have at least one iSports market for this sport."""
    db = get_db()
    cursor = db.markets.find(
        {
            "source": "isports",
            "odds_sport": sport,
            "isports_match_id": {"$exists": True, "$ne": ""},
        },
        {"isports_match_id": 1, "_id": 0},
    )
    rows = await cursor.to_list(5000)
    return {str(r["isports_match_id"]) for r in rows if r.get("isports_match_id")}


def _schedule_filter_new(sport: str, existing: set[str]):
    """Top-league/NBA filter, excluding matches already imported."""
    base = _schedule_filter(sport)

    def fn(rows: list[dict]) -> list[dict]:
        return [m for m in base(rows) if str(m.get("matchId")) not in existing]

    return fn


def _resolve_after(sport: str) -> timedelta:
    if sport == "basketball":
        return RESOLVE_AFTER_BASKETBALL
    return RESOLVE_AFTER_FOOTBALL


async def create_session(sport: str, amount: int = 5) -> dict:
    sport = sport.strip().lower()
    if sport not in ("football", "basketball"):
        raise HTTPException(status_code=400, detail="sport_not_supported")
    amount = min(max(int(amount), 1), 20)
    existing = await _existing_isports_match_ids(sport)
    try:
        _, pool = await load_schedule_until_enough(
            min_filtered=amount,
            max_days=7,
            filter_fn=_schedule_filter_new(sport, existing),
            sport=sport,
        )
    except IsportsNotConfiguredError:
        raise HTTPException(status_code=503, detail="isports_api_not_configured") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail="isports_api_error") from exc

    if not pool:
        raise HTTPException(status_code=404, detail="no_matches")

    matches = pool[:amount]
    if not matches:
        raise HTTPException(status_code=404, detail="no_matches")

    session_id = secrets.token_urlsafe(16)
    match_ids = [str(m["matchId"]) for m in matches]
    db = get_db()
    await db.isports_auto_sessions.insert_one(
        {
            "id": session_id,
            "sport": sport,
            "match_ids": match_ids,
            "matches": matches,
            "built_at": now(),
            "expires_at": now() + SESSION_TTL,
        }
    )
    pref = get_bookmaker_pref()
    return {
        "sessionId": session_id,
        "sport": sport,
        "total": len(match_ids),
        "requested": amount,
        "available": len(pool),
        "status": "ready",
        "oddsBookmaker": pref.label,
        "oddsBookmakerKey": pref.key,
    }


async def _load_session(session_id: str) -> dict:
    db = get_db()
    doc = await db.isports_auto_sessions.find_one({"id": session_id})
    if doc is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    exp = doc.get("expires_at")
    if exp and isinstance(exp, datetime):
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < now():
            raise HTTPException(status_code=410, detail="session_expired")
    return doc


def _match_by_id(session: dict, match_id: str) -> Optional[dict]:
    for m in session.get("matches") or []:
        if str(m.get("matchId")) == str(match_id):
            return m
    return None


def _resolve_football_winner_odds(
    mid: str,
    *,
    europe_rows: list[dict],
    main_europe_rows: list[str],
) -> Optional[tuple[tuple[float, float, float], str]]:
    """Try configured bookmaker, then fallbacks, until 1X2 odds are found."""
    for pref in iter_bookmaker_fallback_prefs():
        eu = pick_europe_from_rows(europe_rows, mid, pref.eu_ids) if pref.eu_ids else None
        if not eu:
            main_ids = pref.main_ids or pref.sub_market_main_ids
            eu = pick_europe_odds(main_europe_rows, mid, company_ids=main_ids or None)
        if eu:
            return eu, pref.label
    eu = pick_europe_odds(main_europe_rows, mid, company_ids=None)
    if eu:
        return eu, "iSports"
    return None


async def _build_football_variants(match: dict) -> list[dict]:
    mid = str(match["matchId"])
    home = str(match.get("homeName", ""))
    away = str(match.get("awayName", ""))

    odds_main_task = fetch_odds_main([mid], company_ids=all_main_company_ids())
    scorers_task = build_player_scorer_variants(match)
    europe_rows_task = fetch_european_rows([mid])
    odds_main, player_variants, europe_rows = await asyncio.gather(
        odds_main_task, scorers_task, europe_rows_task
    )
    if isinstance(odds_main, Exception):
        raise odds_main
    if not isinstance(odds_main, dict):
        odds_main = {}
    if not isinstance(player_variants, list):
        player_variants = []
    if isinstance(europe_rows, Exception):
        log.warning("european rows fetch failed: %s", europe_rows)
        europe_rows = []
    elif not isinstance(europe_rows, list):
        europe_rows = []

    variants: list[dict] = []

    resolved = _resolve_football_winner_odds(
        mid,
        europe_rows=europe_rows,
        main_europe_rows=odds_main.get("europeOdds") or [],
    )
    if resolved:
        eu, winner_source = resolved
        home_o, _draw_o, away_o = eu
        yes_odds, no_odds = _apply_house_edge(home_o, away_o)
        variants.append(
            {
                "key": "match_winner",
                "label": f"{home} - {away}",
                "yesLabel": home,
                "noLabel": away,
                "yesOdds": round(yes_odds, 4),
                "noOdds": round(no_odds, 4),
                "betKind": "match_winner",
                "line": None,
                "isMain": True,
                "oddsSource": winner_source,
            }
        )

    if isinstance(player_variants, list):
        variants.extend(player_variants)

    return variants


def _resolve_basketball_moneyline(
    mid: str,
    money_rows: list[str],
) -> Optional[tuple[tuple[float, float], str]]:
    for pref in iter_bookmaker_fallback_prefs():
        main_ids = pref.main_ids or pref.sub_market_main_ids
        pair = pick_basketball_moneyline(money_rows, mid, company_ids=main_ids or None)
        if pair:
            return pair, pref.label
    pair = pick_basketball_moneyline(money_rows, mid, company_ids=None)
    if pair:
        return pair, "iSports"
    return None


async def _build_basketball_variants(match: dict) -> list[dict]:
    """NBA money line only — no spread/total/player props."""
    mid = str(match["matchId"])
    home = str(match.get("homeName", ""))
    away = str(match.get("awayName", ""))

    odds_data = await fetch_basketball_odds_fulltime()
    money_rows = odds_data.get("moneyLine") if isinstance(odds_data, dict) else []
    if not isinstance(money_rows, list):
        money_rows = []

    resolved = _resolve_basketball_moneyline(mid, money_rows)
    if not resolved:
        return []

    pair, source_label = resolved
    home_o, away_o = pair
    yes_odds, no_odds = _apply_house_edge(home_o, away_o)
    return [
        {
            "key": "match_winner",
            "label": f"{home} - {away}",
            "yesLabel": home,
            "noLabel": away,
            "yesOdds": round(yes_odds, 4),
            "noOdds": round(no_odds, 4),
            "betKind": "match_winner",
            "line": None,
            "isMain": True,
            "oddsSource": source_label,
        }
    ]


async def _build_variants(match: dict, *, sport: str) -> list[dict]:
    if sport == "basketball":
        return await _build_basketball_variants(match)
    return await _build_football_variants(match)


async def get_session_page(session_id: str, page: int, per_page: int = 1) -> dict:
    session = await _load_session(session_id)
    match_ids: list[str] = session.get("match_ids") or []
    total = len(match_ids)
    if total == 0:
        raise HTTPException(status_code=404, detail="no_matches")
    page = max(0, min(page, total - 1))
    per_page = max(1, min(per_page, 1))
    mid = match_ids[page]
    match = _match_by_id(session, mid)
    if not match:
        raise HTTPException(status_code=404, detail="match_not_found")

    sport = str(session.get("sport") or "football").strip().lower()

    try:
        variants = await _build_variants(match, sport=sport)
    except IsportsNotConfiguredError:
        raise HTTPException(status_code=503, detail="isports_api_not_configured") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail="isports_api_error") from exc

    mt = match_time_dt(match)
    return {
        "sessionId": session_id,
        "sport": sport,
        "page": page,
        "total": total,
        "match": {
            "matchId": mid,
            "homeName": match.get("homeName"),
            "awayName": match.get("awayName"),
            "leagueName": match.get("leagueName"),
            "leagueShortName": match.get("leagueShortName"),
            "matchTime": int(match.get("matchTime") or 0),
            "eventDate": format_event_date(mt),
            "status": match.get("status"),
        },
        "variants": variants,
        "subMarketsAvailable": sum(1 for v in variants if not v.get("isMain")),
        "oddsBookmaker": get_bookmaker_pref().label,
    }


def _market_id(
    match_id: str,
    bet_kind: str,
    line: Optional[float],
    *,
    player_id: Optional[str] = None,
) -> str:
    if bet_kind == "player_scores" and player_id:
        return f"isports-{match_id}-player-{player_id}"
    if line is None:
        return f"isports-{match_id}-{bet_kind}"
    return f"isports-{match_id}-{bet_kind}-{_norm_line(line)}"


def _title(
    home: str,
    away: str,
    bet_kind: str,
    line: Optional[float],
    *,
    player_name: Optional[str] = None,
) -> str:
    base = f"{home} - {away}"
    if bet_kind == "player_scores" and player_name:
        return f"{base}: {player_name} scores"
    if bet_kind in ("match_winner", "match_home"):
        return base
    if bet_kind == "goals_over" and line is not None:
        return f"{base}: Over {line:g} goals"
    if bet_kind == "corners_over" and line is not None:
        return f"{base}: Over {line:g} corners"
    if bet_kind == "btts":
        return f"{base}: Both teams to score"
    return base


async def create_markets_from_variants(
    session_id: str,
    match_id: str,
    variant_keys: list[str],
) -> dict:
    session = await _load_session(session_id)
    match = _match_by_id(session, str(match_id))
    if not match:
        raise HTTPException(status_code=404, detail="match_not_found")

    home = str(match.get("homeName", ""))
    away = str(match.get("awayName", ""))
    sport = str(session.get("sport") or "football").strip().lower()
    variants = await _build_variants(match, sport=sport)
    by_key = {v["key"]: v for v in variants}

    db = get_db()
    preset_rows = await db.presets.find().to_list(500)
    lookup = _preset_lookup(preset_rows)
    main_image = _resolve_image(home, away, lookup)

    mt = match_time_dt(match)
    event_date = mt
    resolve_after = (mt + _resolve_after(sport)) if mt else None

    created: list[dict] = []
    skipped: list[str] = []

    for key in variant_keys:
        v = by_key.get(key)
        if not v:
            skipped.append(f"{key} (unavailable)")
            continue
        bet_kind = v["betKind"]
        line = v.get("line")
        player_id = v.get("playerId")
        market_id = _market_id(
            str(match_id), bet_kind, line, player_id=str(player_id) if player_id else None
        )
        existing = await db.markets.find_one({"id": market_id})
        if existing:
            skipped.append(f"{v['label']} (already exists)")
            continue

        yes_odds = float(v["yesOdds"])
        no_odds = float(v["noOdds"])
        if bet_kind == "player_scores":
            pname = str(v.get("playerName", ""))
            title = _title(home, away, bet_kind, line, player_name=pname)
            image = _resolve_image_for_name(pname, lookup) or main_image
        else:
            title = _title(home, away, bet_kind, line)
            image = main_image

        image = safe_image_url(image) if image else None

        doc: dict[str, Any] = {
            "id": market_id,
            "title": title,
            "image": image,
            "yes_label": v["yesLabel"],
            "no_label": v["noLabel"],
            "yes_odds": Decimal(str(round(yes_odds, 4))),
            "no_odds": Decimal(str(round(no_odds, 4))),
            "status": "active",
            "outcome": None,
            "created_at": now(),
            "event_date": event_date,
            "source": "isports",
            "odds_sport": sport,
            "external": True,
            "isports_match_id": str(match_id),
            "bet_kind": bet_kind,
            "auto_resolve": True,
            "match_time": mt,
            "resolve_after": resolve_after,
        }
        if line is not None:
            doc["line"] = float(line)
        if player_id:
            doc["isports_player_id"] = str(player_id)
            doc["player_name"] = str(v.get("playerName", ""))

        await db.markets.insert_one(doc)
        created.append(
            _created_admin_row(
                market_id=market_id,
                title=title,
                image=image,
                home=v["yesLabel"],
                away=v["noLabel"],
                yes_odds=yes_odds,
                no_odds=no_odds,
                event_date=event_date,
            )
        )

    if not created and skipped:
        raise HTTPException(
            status_code=422,
            detail={"error": "nothing_created", "skipped": skipped},
        )

    return {"created": created, "skipped": skipped, "count": len(created)}
