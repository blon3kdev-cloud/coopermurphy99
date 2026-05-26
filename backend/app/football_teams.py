"""Top-football-team whitelist — re-exports shared top-entities helpers."""
from __future__ import annotations

from .top_sports_entities import (
    TOP_LEAGUES_BY_SPORT,
    event_has_top_entity,
    is_top_entity,
)

TOP_LEAGUE_SLUGS = TOP_LEAGUES_BY_SPORT["football"]


def is_top_team(name: str) -> bool:
    return is_top_entity(name, "football")


def event_has_top_team(home: str, away: str) -> bool:
    return event_has_top_entity(home, away, "football")
