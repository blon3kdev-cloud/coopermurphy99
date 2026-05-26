"""Discrete YES/NO betting markets — public listing endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException, Query

from ..cache import cached_async
from ..db import get_db
from ..market_categories import available_filters, market_filter_id
from ..market_bet_stats import bet_stats_by_market
from ..market_utils import (
    format_event_date,
    is_open_for_betting,
    market_bet_start_at,
    parse_iso_date,
)

router = APIRouter(prefix="/api/markets", tags=["markets"])


def _row_to_dict(r: dict) -> dict:
    event_dt = market_bet_start_at(r)
    display_date = format_event_date(event_dt) if event_dt else r["created_at"].strftime("%d.%m.%Y")
    return {
        "id": r["id"],
        "title": r["title"],
        "image": r.get("image"),
        "date": display_date,
        "eventDate": event_dt.isoformat() if event_dt else None,
        "yesLabel": r.get("yes_label", "Yes"),
        "noLabel": r.get("no_label", "No"),
        "yesOdds": f"{float(r['yes_odds']):.2f}x".replace(".", ","),
        "noOdds": f"{float(r['no_odds']):.2f}x".replace(".", ","),
        "status": r["status"],
        "categoryId": market_filter_id(r),
    }


def _featured_sort_key(row: dict, stats: dict[str, dict]) -> tuple:
    """1. bet count  2. money  3. has image  4. earliest event."""
    mid = row["id"]
    s = stats.get(mid, {})
    bet_count = int(s.get("bet_count", 0))
    money = float(s.get("money", 0))
    has_image = 1 if row.get("image") else 0
    event_dt = parse_iso_date(row.get("eventDate"))
    if event_dt is None:
        event_dt = datetime.max.replace(tzinfo=timezone.utc)
    return (-bet_count, -money, -has_image, event_dt)


async def _open_markets(*, limit: int = 200) -> list[dict]:
    cursor = get_db().markets.find({"status": "active"}).sort("created_at", -1).limit(limit)
    return [r async for r in cursor if is_open_for_betting(r)]


@router.get("/filters")
async def list_filters() -> list[dict]:
    rows = await _open_markets()
    return available_filters(rows)


async def _featured_payload() -> list[dict]:
    rows = await _open_markets(limit=100)
    if not rows:
        return []
    stats = await bet_stats_by_market([str(r["id"]) for r in rows])
    ranked = sorted(
        [_row_to_dict(r) for r in rows],
        key=lambda item: _featured_sort_key(item, stats),
    )
    return ranked[:4]


async def _all_markets_payload() -> list[dict]:
    rows = await _open_markets()
    out = [_row_to_dict(r) for r in rows]
    out.sort(
        key=lambda item: parse_iso_date(item.get("eventDate"))
        or datetime.max.replace(tzinfo=timezone.utc)
    )
    return out


@router.get("/featured")
async def list_featured() -> list[dict]:
    return await cached_async("markets:featured", 30.0, _featured_payload)


async def _markets_page(*, limit: int, cursor: str | None) -> dict:
    all_items = await cached_async("markets:all", 30.0, _all_markets_payload)
    start = 0
    if cursor:
        for i, item in enumerate(all_items):
            if str(item["id"]) == str(cursor):
                start = i + 1
                break
    page = all_items[start : start + limit]
    has_more = start + limit < len(all_items)
    return {
        "items": page,
        "nextCursor": str(page[-1]["id"]) if page and has_more else None,
    }


@router.get("")
async def list_all(
    limit: Optional[int] = Query(default=None, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    if limit is not None:
        return await _markets_page(limit=limit, cursor=cursor)
    return await cached_async("markets:all", 30.0, _all_markets_payload)


@router.get("/{market_id}")
async def get_one(market_id: str) -> dict:
    r = await get_db().markets.find_one({"id": market_id})
    if r is None or not is_open_for_betting(r):
        raise HTTPException(status_code=404, detail="not found")
    return _row_to_dict(r)
