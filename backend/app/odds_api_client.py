"""Odds-API.io client — sports, events, and match odds."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from .config import get_settings

log = logging.getLogger(__name__)

BASE = "https://api.odds-api.io/v3"
FALLBACK_BOOKMAKERS = "Superbet,Betclic PL"


def _api_key() -> str:
    key = get_settings().odds_api_key.strip()
    if not key:
        raise ValueError("ODDS_API_KEY is not configured")
    return key


async def _get(path: str, *, params: Optional[dict[str, Any]] = None) -> Any:
    p = dict(params or {})
    if path not in ("/sports",):
        p.setdefault("apiKey", _api_key())
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(f"{BASE}{path}", params=p)
        res.raise_for_status()
        return res.json()


async def list_sports() -> list[dict]:
    data = await _get("/sports")
    return data if isinstance(data, list) else []


async def list_events(sport: str, *, limit: int = 50, league: Optional[str] = None) -> list[dict]:
    params: dict[str, Any] = {"sport": sport, "limit": min(max(limit, 1), 100)}
    if league:
        params["league"] = league
    try:
        data = await _get("/events", params=params)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return []
        raise
    return data if isinstance(data, list) else []


async def list_events_from_top_leagues(sport: str, *, limit_per_league: int = 30) -> list[dict]:
    from .top_sports_entities import TOP_LEAGUES_BY_SPORT

    leagues = TOP_LEAGUES_BY_SPORT.get(sport, ())
    seen: set[int] = set()
    out: list[dict] = []
    for league in leagues:
        rows = await list_events(sport, limit=limit_per_league, league=league)
        for row in rows:
            eid = row.get("id")
            if eid is None or eid in seen:
                continue
            seen.add(int(eid))
            out.append(row)
    return out


async def list_football_events_from_top_leagues(*, limit_per_league: int = 30) -> list[dict]:
    return await list_events_from_top_leagues("football", limit_per_league=limit_per_league)


async def selected_bookmakers() -> str:
    try:
        data = await _get("/bookmakers/selected")
        names = data.get("bookmakers") if isinstance(data, dict) else None
        if isinstance(names, list) and names:
            return ",".join(str(n) for n in names)
    except Exception:
        log.warning("could not load selected bookmakers, using fallback")
    return FALLBACK_BOOKMAKERS


async def fetch_odds_multi(event_ids: list[int]) -> list[dict]:
    if not event_ids:
        return []
    bookmakers = await selected_bookmakers()
    ids = ",".join(str(i) for i in event_ids[:10])
    data = await _get(
        "/odds/multi",
        params={"eventIds": ids, "bookmakers": bookmakers},
    )
    return data if isinstance(data, list) else []


from .market_utils import parse_iso_date


def pick_upcoming_events(events: list[dict], count: int) -> list[dict]:
    now = datetime.now(timezone.utc)
    pending = [
        e
        for e in events
        if str(e.get("status", "")).lower() in ("pending", "not_started", "")
        and e.get("home")
        and e.get("away")
    ]
    pending.sort(
        key=lambda e: parse_iso_date(str(e.get("date", "9999-01-01T00:00:00Z")))
        or datetime.max.replace(tzinfo=timezone.utc)
    )
    upcoming = [
        e
        for e in pending
        if (parse_iso_date(str(e["date"])) or datetime.min.replace(tzinfo=timezone.utc)) >= now
    ]
    pool = upcoming if upcoming else pending
    return pool[: max(count, 1)]


def extract_ml_odds(odds_row: dict) -> Optional[tuple[float, float]]:
    bookmakers = odds_row.get("bookmakers") or {}
    for markets in bookmakers.values():
        if not isinstance(markets, list):
            continue
        for market in markets:
            if market.get("name") != "ML":
                continue
            odds_list = market.get("odds") or []
            if not odds_list:
                continue
            row = odds_list[0]
            try:
                home = float(row["home"])
                away = float(row["away"])
            except (KeyError, TypeError, ValueError):
                continue
            if home > 0 and away > 0:
                return home, away
    return None
