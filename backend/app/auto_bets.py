"""Create market bets from Odds-API.io events with preset image matching."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

AUTO_BET_HOUSE_EDGE = 0.10

from fastapi import HTTPException

from .db import get_db, now
from .market_utils import format_event_date, parse_iso_date
from .odds_api_client import (
    extract_ml_odds,
    fetch_odds_multi,
    list_events,
    list_events_from_top_leagues,
    pick_upcoming_events,
)
from .preset_matching import name_matches
from .safe_url import safe_image_url
from .top_sports_entities import (
    TOP_LEAGUES_BY_SPORT,
    event_has_top_entity,
    sport_has_whitelist,
)


def _norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


def _preset_lookup(rows: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in rows:
        payload = row.get("payload") or {}
        image = safe_image_url(payload.get("imageUrl"))
        if not image:
            continue
        names = payload.get("names") or []
        if isinstance(names, list):
            for n in names:
                if n:
                    out[_norm(n)] = image
        preset_name = row.get("name")
        if preset_name:
            out[_norm(preset_name)] = image
    return out


def _apply_house_edge(yes_odds: float, no_odds: float) -> tuple[float, float]:
    """Reduce decimal odds so the house keeps ~AUTO_BET_HOUSE_EDGE margin."""
    factor = 1.0 + AUTO_BET_HOUSE_EDGE
    return yes_odds / factor, no_odds / factor


def _created_admin_row(
    *,
    market_id: str,
    title: str,
    image: Optional[str],
    home: str,
    away: str,
    yes_odds: float,
    no_odds: float,
    event_date: Optional[datetime],
) -> dict:
    """Same shape as GET /admin/bets rows (frontend expects yes/no numbers)."""
    return {
        "id": market_id,
        "title": title,
        "image": image,
        "eventDate": format_event_date(event_date),
        "yesLabel": home,
        "noLabel": away,
        "yes": round(yes_odds, 4),
        "no": round(no_odds, 4),
        "status": "active",
        "bets": 0,
        "volume": 0.0,
    }


def _resolve_image_for_name(name: str, lookup: dict[str, str]) -> Optional[str]:
    if not name or not lookup:
        return None
    direct = lookup.get(_norm(name))
    if direct:
        return direct
    for alias, img in lookup.items():
        if name_matches(name, alias):
            return img
    return None


def _resolve_image(home: str, away: str, lookup: dict[str, str]) -> Optional[str]:
    for team in (home, away):
        img = _resolve_image_for_name(team, lookup)
        if img:
            return img
    return None


def _filter_top_entities(events: list[dict], sport: str) -> list[dict]:
    upcoming = pick_upcoming_events(events, 500)
    return [
        e
        for e in upcoming
        if event_has_top_entity(str(e.get("home", "")), str(e.get("away", "")), sport)
    ]


async def _load_event_pool(sport: str) -> list[dict]:
    leagues = TOP_LEAGUES_BY_SPORT.get(sport, ())
    if leagues:
        events = await list_events_from_top_leagues(sport, limit_per_league=40)
        if not events:
            events = await list_events(sport, limit=200)
    else:
        events = await list_events(sport, limit=200)
    if sport_has_whitelist(sport):
        pool = _filter_top_entities(events, sport)
        if pool:
            return pool
        raise HTTPException(status_code=404, detail="no_top_entity_events")
    pool = pick_upcoming_events(events, 100)
    if not pool:
        raise HTTPException(status_code=404, detail="no_events")
    return pool


async def create_bets_from_odds(sport: str, amount: int) -> dict:
    amount = min(max(amount, 1), 20)
    sport_slug = sport.strip().lower()
    db = get_db()
    pool = await _load_event_pool(sport_slug)

    preset_rows = await db.presets.find().to_list(500)
    lookup = _preset_lookup(preset_rows)

    created: list[dict] = []
    skipped: list[str] = []
    idx = 0

    while len(created) < amount and idx < len(pool):
        batch_events = pool[idx : idx + 10]
        idx += 10
        odds_rows = await fetch_odds_multi([int(e["id"]) for e in batch_events])
        odds_by_id = {int(r["id"]): r for r in odds_rows if r.get("id") is not None}

        for ev in batch_events:
            if len(created) >= amount:
                break
            eid = int(ev["id"])
            home = str(ev["home"])
            away = str(ev["away"])
            if sport_has_whitelist(sport_slug) and not event_has_top_entity(home, away, sport_slug):
                skipped.append(f"{home} vs {away} (not a top team/player)")
                continue
            odds_data = odds_by_id.get(eid)
            if not odds_data:
                skipped.append(f"{home} vs {away} (no odds)")
                continue
            ml = extract_ml_odds(odds_data)
            if not ml:
                skipped.append(f"{home} vs {away} (no ML market)")
                continue
            yes_odds, no_odds = _apply_house_edge(*ml)
            market_id = f"odds-{sport}-{eid}"
            existing = await db.markets.find_one({"id": market_id})
            if existing:
                skipped.append(f"{home} vs {away} (already exists)")
                continue

            title = f"{home} - {away}"
            image = safe_image_url(_resolve_image(home, away, lookup))
            raw_date = ev.get("date") or odds_data.get("date")
            event_date = parse_iso_date(raw_date)

            await db.markets.insert_one(
                {
                    "id": market_id,
                    "title": title,
                    "image": image,
                    "yes_label": home,
                    "no_label": away,
                    "yes_odds": Decimal(str(round(yes_odds, 4))),
                    "no_odds": Decimal(str(round(no_odds, 4))),
                    "status": "active",
                    "outcome": None,
                    "created_at": now(),
                    "event_date": event_date,
                    "odds_event_id": eid,
                    "odds_sport": sport_slug,
                }
            )
            created.append(
                _created_admin_row(
                    market_id=market_id,
                    title=title,
                    image=image,
                    home=home,
                    away=away,
                    yes_odds=yes_odds,
                    no_odds=no_odds,
                    event_date=event_date,
                )
            )

    if not created:
        detail: dict = {"error": "nothing_created", "skipped": skipped[:30]}
        if sport_has_whitelist(sport_slug):
            detail["hint"] = "no_top_entity_match_with_odds"
        raise HTTPException(status_code=422, detail=detail)

    return {"created": created, "skipped": skipped, "count": len(created)}
