"""iSports bookmaker preference — main (18) vs European (200+) company IDs."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from .config import get_settings

# companyIdMain from /sport/football/bookmaker (0 = not in main odds API).
_MAIN_BOOKMAKERS: dict[str, tuple[str, ...]] = {
    "crown": ("3",),
    "bet365": ("8",),
    "ladbrokes": ("4",),
    "williamhill": ("9",),
    "bwin": ("49",),
    "sbobet": ("31",),
}

# companyIdEu — European Odds (200+); Betclic is not in the main API.
_EU_BOOKMAKERS: dict[str, tuple[str, ...]] = {
    "betclic": ("1290", "1347", "827"),
    "betclic.pl": ("1290",),
    "betclick": ("463", "742"),
}

_LABELS: dict[str, str] = {
    "betclic": "Betclic.pl",
    "betclic.pl": "Betclic.pl",
    "bet365": "Bet365",
    "crown": "Crown",
    "ladbrokes": "Ladbrokes",
    "williamhill": "William Hill",
    "bwin": "Bwin",
    "sbobet": "Sbobet",
}

# Sub-markets (goals O/U, corners, BTTS) only exist on the main 18-bookmaker API.
_SUB_MARKET_FALLBACK_MAIN = ("8",)  # Bet365


@dataclass(frozen=True)
class IsportsBookmakerPref:
    key: str
    label: str
    main_ids: tuple[str, ...]
    eu_ids: tuple[str, ...]
    sub_market_main_ids: tuple[str, ...]


def _norm_key(raw: str) -> str:
    return raw.strip().lower().replace(" ", "").replace("_", "").replace("-", "")


def resolve_bookmaker_key(raw: Optional[str] = None) -> str:
    key = _norm_key(raw or get_settings().isports_odds_bookmaker or "betclic")
    if key in _MAIN_BOOKMAKERS or key in _EU_BOOKMAKERS:
        return key
    if key in ("betclicpl",):
        return "betclic.pl"
    return "bet365"


@lru_cache(maxsize=8)
def get_bookmaker_pref(key: Optional[str] = None) -> IsportsBookmakerPref:
    resolved = resolve_bookmaker_key(key)
    main_ids = _MAIN_BOOKMAKERS.get(resolved, ())
    eu_ids = _EU_BOOKMAKERS.get(resolved, ())
    sub_main = main_ids if main_ids else _SUB_MARKET_FALLBACK_MAIN
    label = _LABELS.get(resolved, resolved)
    return IsportsBookmakerPref(
        key=resolved,
        label=label,
        main_ids=main_ids,
        eu_ids=eu_ids,
        sub_market_main_ids=sub_main,
    )


_FALLBACK_BOOKMAKER_KEYS: tuple[str, ...] = (
    "betclic",
    "bet365",
    "bwin",
    "williamhill",
    "ladbrokes",
    "crown",
    "sbobet",
)


def all_main_company_ids() -> tuple[str, ...]:
    """Union of main-API company IDs (for a single odds/main fetch)."""
    seen: list[str] = []
    for ids in _MAIN_BOOKMAKERS.values():
        for cid in ids:
            if cid not in seen:
                seen.append(cid)
    for cid in _SUB_MARKET_FALLBACK_MAIN:
        if cid not in seen:
            seen.append(cid)
    return tuple(seen)


def all_eu_company_ids() -> tuple[str, ...]:
    """Union of European-odds company IDs (for a single european/all fetch)."""
    seen: list[str] = []
    for ids in _EU_BOOKMAKERS.values():
        for cid in ids:
            if cid not in seen:
                seen.append(cid)
    return tuple(seen)


def iter_bookmaker_fallback_prefs() -> tuple[IsportsBookmakerPref, ...]:
    """Configured bookmaker first, then other known providers."""
    primary = get_bookmaker_pref()
    keys: list[str] = [primary.key]
    for key in _FALLBACK_BOOKMAKER_KEYS:
        if key not in keys:
            keys.append(key)
    return tuple(get_bookmaker_pref(k) for k in keys)
