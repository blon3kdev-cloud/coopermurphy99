"""Market category filters for the Bety listing (derived from stored fields)."""
from __future__ import annotations

import re
from typing import Optional

# filter id -> display label (only shown when at least one open market matches)
FILTER_LABELS: dict[str, str] = {
    "pilka": "Piłka Nożna",
    "nba": "NBA",
    "tennis": "Tenis",
    "mlb": "MLB",
    "nfl": "NFL",
    "mma": "MMA",
    "boks": "Boks",
    "esports": "Esports",
    "filmy": "Filmy & Seriale",
    "smieszne": "Śmieszne",
}

_ODDS_SPORT_TO_FILTER: dict[str, str] = {
    "football": "pilka",
    "basketball": "nba",
    "tennis": "tennis",
    "baseball": "mlb",
    "american-football": "nfl",
    "mixed-martial-arts": "mma",
    "boxing": "boks",
    "esports": "esports",
}

_FILMY_RE = re.compile(
    r"\b(film|filmu|serial|sezon|oscar|emmy|netflix|disney|hbo|kin[aey]|aktor|aktorka)\b",
    re.I,
)
_SMIESZNE_RE = re.compile(
    r"\b(smieszne|śmieszne|mem|memy|lol|dowcip|żart|zart|komed)\b",
    re.I,
)


def market_filter_id(market: dict) -> Optional[str]:
    """Return filter chip id for a market, or None if uncategorized."""
    explicit = market.get("category")
    if isinstance(explicit, str) and explicit.strip():
        cid = explicit.strip().lower()
        if cid in FILTER_LABELS:
            return cid

    sport = market.get("odds_sport")
    if isinstance(sport, str) and sport.strip():
        mapped = _ODDS_SPORT_TO_FILTER.get(sport.strip().lower())
        if mapped:
            return mapped
    if market.get("source") == "isports":
        return "pilka"

    text = " ".join(
        str(market.get(k) or "")
        for k in ("title", "yes_label", "no_label")
    )
    if _SMIESZNE_RE.search(text):
        return "smieszne"
    if _FILMY_RE.search(text):
        return "filmy"
    return None


def available_filters(markets: list[dict]) -> list[dict]:
    """[{id, label}] for categories that have at least one market."""
    seen: set[str] = set()
    for m in markets:
        fid = market_filter_id(m)
        if fid:
            seen.add(fid)
    order = list(FILTER_LABELS.keys())
    return [{"id": fid, "label": FILTER_LABELS[fid]} for fid in order if fid in seen]
