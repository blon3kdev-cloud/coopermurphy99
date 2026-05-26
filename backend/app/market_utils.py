"""Shared market helpers — event dates and open/closed checks."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from .db import as_utc, now

WARSAW = ZoneInfo("Europe/Warsaw")
_DISPLAY_DATE_RE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})$")


def parse_iso_date(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return as_utc(raw)
    if isinstance(raw, (int, float)):
        try:
            return datetime.fromtimestamp(int(raw), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None
    s = str(raw).strip()
    if not s:
        return None
    m = _DISPLAY_DATE_RE.match(s)
    if m:
        day, month, year, hour, minute = (int(x) for x in m.groups())
        return datetime(year, month, day, hour, minute, tzinfo=WARSAW).astimezone(timezone.utc)
    s = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def market_bet_start_at(market: dict) -> Optional[datetime]:
    """Kickoff instant in UTC. Prefer match_time (real start) over event_date."""
    mt = as_utc(market.get("match_time"))
    if mt is not None:
        return mt
    return parse_iso_date(market.get("event_date"))


def format_event_date(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    normalized = as_utc(dt)
    if normalized is None:
        return ""
    return normalized.astimezone(WARSAW).strftime("%d.%m.%Y %H:%M")


def format_bet_day(dt: Optional[datetime]) -> str:
    """Calendar day for grouping bets — Europe/Warsaw."""
    if dt is None:
        return ""
    normalized = as_utc(dt)
    if normalized is None:
        return ""
    return normalized.astimezone(WARSAW).strftime("%d.%m.%Y")


def is_open_for_betting(market: dict) -> bool:
    if market.get("status") != "active":
        return False
    start = market_bet_start_at(market)
    if start is None:
        return True
    return start > now()
