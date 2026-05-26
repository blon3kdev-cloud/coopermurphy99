"""Top teams / players whitelist loaded from per-sport JSON files."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

_FOOTBALL_PLAYERS_FILE = "top_football_players.json"
_FOOTBALL_NATIONALITIES_FILE = "top_football_nationalities.json"

_SPORT_DATA_FILES: dict[str, str] = {
    "football": "top_football_teams.json",
    "tennis": "top_tennis_players.json",
    "boxing": "top_boxing_fighters.json",
    "mixed-martial-arts": "top_mma_fighters.json",
    "esports": "top_esports_teams.json",
    "baseball": "top_baseball_teams.json",
    "basketball": "top_basketball_teams.json",
    "american-football": "top_american_football_teams.json",
}

TOP_LEAGUES_BY_SPORT: dict[str, tuple[str, ...]] = {
    "football": (
        "england-premier-league",
        "spain-laliga",
        "germany-bundesliga",
        "italy-serie-a",
        "france-ligue-1",
        "uefa-champions-league",
        "uefa-europa-league",
        "portugal-primeira-liga",
        "netherlands-eredivisie",
    ),
    "basketball": (
        "usa-nba",
        "international-euroleague",
    ),
    "baseball": ("usa-mlb",),
    "american-football": ("usa-nfl",),
    "tennis": (
        "atp-french-open-men-singles",
        "wta-french-open-women-singles",
    ),
    "esports": (
        "league-of-legends-lck",
        "league-of-legends-lec",
        "league-of-legends-lpl",
        "league-of-legends-lcs",
        "dota-dreamleague",
        "valorant-champions-tour-americas",
        "counter-strike-blast-premier",
        "counter-strike-iem",
    ),
}


def _norm(name: str) -> str:
    return " ".join(str(name).strip().lower().split())


@lru_cache(maxsize=None)
def _alias_set(sport: str) -> frozenset[str]:
    filename = _SPORT_DATA_FILES.get(sport)
    if not filename:
        return frozenset()
    path = _DATA_DIR / filename
    raw = json.loads(path.read_text(encoding="utf-8"))
    aliases: set[str] = set()
    for entry in raw.get("teams", []):
        for name in entry.get("names", []):
            n = _norm(name)
            if n:
                aliases.add(n)
    return frozenset(aliases)


def sport_has_whitelist(sport: str) -> bool:
    return sport in _SPORT_DATA_FILES


def is_top_entity(name: str, sport: str) -> bool:
    """True if name matches the top-entities whitelist for this sport."""
    entity = _norm(name)
    if not entity:
        return False
    aliases = _alias_set(sport)
    if not aliases:
        return False
    if entity in aliases:
        return True
    for alias in aliases:
        # Avoid false positives like "Inter Kashi" matching alias "inter".
        if len(alias) < 6 or len(entity) < 6:
            continue
        if alias in entity or entity in alias:
            return True
    return False


def event_has_top_entity(home: str, away: str, sport: str) -> bool:
    return is_top_entity(home, sport) or is_top_entity(away, sport)


def _name_hits_alias(entity: str, alias: str) -> bool:
    if entity == alias:
        return True
    if len(alias) < 4 or len(entity) < 4:
        return False
    return alias in entity or entity in alias


@lru_cache(maxsize=None)
def _team_alias_groups(sport: str) -> tuple[frozenset[str], ...]:
    """Each frozenset is one club with all known name variants (normalized)."""
    filename = _SPORT_DATA_FILES.get(sport)
    if not filename:
        return ()
    path = _DATA_DIR / filename
    raw = json.loads(path.read_text(encoding="utf-8"))
    groups: list[frozenset[str]] = []
    for entry in raw.get("teams", []):
        names = {_norm(n) for n in entry.get("names", []) if _norm(n)}
        if names:
            groups.append(frozenset(names))
    return tuple(groups)


def same_team(name_a: str, name_b: str, sport: str = "football") -> bool:
    """True when two labels refer to the same club (e.g. Man City / Manchester City)."""
    a, b = _norm(name_a), _norm(name_b)
    if not a or not b:
        return False
    if a == b or _name_hits_alias(a, b):
        return True
    for group in _team_alias_groups(sport):
        hit_a = any(_name_hits_alias(a, alias) for alias in group)
        hit_b = any(_name_hits_alias(b, alias) for alias in group)
        if hit_a and hit_b:
            return True
    return False


_EXCLUDED_FOOTBALL_LEAGUE_HINTS: tuple[str, ...] = (
    "u19",
    "u21",
    "u23",
    "u18",
    "u20",
    "youth",
    "junior",
    "junioren",
    "reserve",
    "reserves",
    "women",
    "femenil",
    "femenina",
    "amateur",
    "friendly",
    "friendlies",
)

# Big Five European domestic leagues (top clubs).
_BIG_FIVE_FOOTBALL_LEAGUE_KEYWORDS: tuple[str, ...] = (
    "premier league",
    "english premier",
    "la liga",
    "laliga",
    "bundesliga",
    "serie a",
    "ligue 1",
    "ligue un",
    "french ligue",
    "france ligue",
    "ligue1",
)

_TOP_CLUB_CUP_KEYWORDS: tuple[str, ...] = (
    "uefa champions",
    "champions league",
    "liga mistrzow",
    "liga mistrzów",
    "europa league",
    "liga europy",
    "conference league",
)

_INTERNATIONAL_FOOTBALL_LEAGUE_KEYWORDS: tuple[str, ...] = (
    "world cup",
    "european championship",
    "uefa euro",
    "euro 20",
    "nations league",
    "international friendly",
    "fifa",
    "world cup qualifier",
    "euro qualifier",
    "european qualifier",
    "copa america",
    "confederations cup",
)

_TOP_FOOTBALL_LEAGUE_KEYWORDS: tuple[str, ...] = (
    *_BIG_FIVE_FOOTBALL_LEAGUE_KEYWORDS,
    *_TOP_CLUB_CUP_KEYWORDS,
    "eredivisie",
    "primeira liga",
    "liga portugal",
    "scottish premiership",
    "super lig",
    "turkish super",
    "belgian pro",
    "austrian bundesliga",
    "swiss super",
    "danish superliga",
    "norwegian eliteserien",
    "swedish allsvenskan",
    "mls",
    "major league soccer",
    "copa libertadores",
    "copa sudamericana",
)


def is_womens_team(name: str) -> bool:
    """Women's sides (W / Women suffix) — excluded from auto-import."""
    n = _norm(name)
    if not n:
        return False
    if "(w)" in n or n.endswith("(w)"):
        return True
    if n.endswith(" w") or n.startswith("w "):
        return True
    markers = (
        " women",
        " wfc",
        " womens",
        " feminine",
        " femenil",
        " femenina",
        " ladies",
    )
    return any(m in n for m in markers)


def is_reserve_or_youth_team(name: str) -> bool:
    """B-sides, U19/U21, youth squads — not senior top-flight."""
    n = _norm(name)
    if not n:
        return False
    markers = (
        " u19",
        " u21",
        " u23",
        " u18",
        " u20",
        " youth",
        " junior",
        " junioren",
        " reserves",
        " reserve",
        " ii",
        " b team",
    )
    if any(m in n for m in markers):
        return True
    if n.endswith(" b") or n.endswith(" ii"):
        return True
    return False


def _football_league_blob(row: dict) -> str:
    return _norm(f"{row.get('leagueName', '')} {row.get('leagueShortName', '')}")


def _league_blob_matches(blob: str, keywords: tuple[str, ...]) -> bool:
    if not blob:
        return False
    if any(ex in blob for ex in _EXCLUDED_FOOTBALL_LEAGUE_HINTS):
        return False
    return any(kw in blob for kw in keywords)


def is_big_five_football_league(row: dict) -> bool:
    """Domestic top-five European leagues (EPL, La Liga, Bundesliga, Serie A, Ligue 1)."""
    blob = _football_league_blob(row)
    if not blob:
        return False
    if "austrian" in blob and "bundesliga" in blob:
        return False
    if "2. bundesliga" in blob or "bundesliga 2" in blob:
        return False
    return _league_blob_matches(blob, _BIG_FIVE_FOOTBALL_LEAGUE_KEYWORDS)


def is_top_club_cup_league(row: dict) -> bool:
    """UEFA club competitions (Champions League, Europa, etc.)."""
    return _league_blob_matches(_football_league_blob(row), _TOP_CLUB_CUP_KEYWORDS)


def is_international_football_league(row: dict) -> bool:
    """Major national-team competitions (World Cup, Euros, Nations League, etc.)."""
    return _league_blob_matches(_football_league_blob(row), _INTERNATIONAL_FOOTBALL_LEAGUE_KEYWORDS)


def is_top_football_league(row: dict) -> bool:
    """True when schedule row is from a recognised top-tier competition."""
    blob = _football_league_blob(row)
    return _league_blob_matches(blob, _TOP_FOOTBALL_LEAGUE_KEYWORDS)


@lru_cache(maxsize=1)
def _nationality_alias_set() -> frozenset[str]:
    path = _DATA_DIR / _FOOTBALL_NATIONALITIES_FILE
    if not path.is_file():
        return frozenset()
    raw = json.loads(path.read_text(encoding="utf-8"))
    aliases: set[str] = set()
    for entry in raw.get("nationalities", []):
        for name in entry.get("names", []):
            n = _norm(name)
            if n:
                aliases.add(n)
    return frozenset(aliases)


def is_top_football_nationality(name: str) -> bool:
    """True when side is on the curated top-national-teams list."""
    entity = _norm(name)
    if not entity:
        return False
    aliases = _nationality_alias_set()
    if not aliases:
        return False
    if entity in aliases:
        return True
    for alias in aliases:
        if len(alias) < 4 or len(entity) < 4:
            continue
        if alias in entity or entity in alias:
            return True
    return False


def _football_league_allowed(row: dict) -> bool:
    """Big-five, UEFA cups, or major international competitions."""
    return (
        is_big_five_football_league(row)
        or is_top_club_cup_league(row)
        or is_international_football_league(row)
    )


def is_top_football_nationality_match(home: str, away: str, row: dict) -> bool:
    """International fixture in an allowed competition (league gate only)."""
    if is_womens_team(home) or is_womens_team(away):
        return False
    if is_reserve_or_youth_team(home) or is_reserve_or_youth_team(away):
        return False
    return is_international_football_league(row)


def is_top_football_club_match(home: str, away: str, row: dict) -> bool:
    """Big-five domestic league or UEFA cup (league gate only)."""
    if is_womens_team(home) or is_womens_team(away):
        return False
    if is_reserve_or_youth_team(home) or is_reserve_or_youth_team(away):
        return False
    return is_big_five_football_league(row) or is_top_club_cup_league(row)


def is_top_football_match(home: str, away: str, row: dict) -> bool:
    """Allowed football league; excludes women's and youth (U) sides."""
    if is_womens_team(home) or is_womens_team(away):
        return False
    if is_reserve_or_youth_team(home) or is_reserve_or_youth_team(away):
        return False
    return _football_league_allowed(row)


def is_nba_match(row: dict) -> bool:
    """True when schedule row is an NBA game (league short name from iSports)."""
    name = _norm(str(row.get("leagueName", "")))
    return name == "nba"


def is_top_nba_match(home: str, away: str, row: dict) -> bool:
    """NBA only + both teams on the basketball (NBA) whitelist."""
    if is_womens_team(home) or is_womens_team(away):
        return False
    if not is_nba_match(row):
        return False
    return is_top_entity(home, "basketball") and is_top_entity(away, "basketball")


@lru_cache(maxsize=1)
def _football_player_entries() -> tuple[dict, ...]:
    path = _DATA_DIR / _FOOTBALL_PLAYERS_FILE
    if not path.is_file():
        return ()
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: list[dict] = []
    for entry in raw.get("players", []):
        names = [_norm(n) for n in entry.get("names", []) if _norm(n)]
        if not names:
            continue
        out.append(
            {
                "names": names,
                "displayName": entry.get("names", [""])[0],
                "team": str(entry.get("team", "")).strip(),
                "league": str(entry.get("league", "")).strip(),
            }
        )
    return tuple(out)


def _player_name_matches(entity: str, alias: str) -> bool:
    if entity == alias:
        return True
    if len(alias) < 4 or len(entity) < 4:
        return False
    return alias in entity or entity in alias


def _find_football_player_entry(name: str) -> Optional[dict]:
    entity = _norm(name)
    if not entity:
        return None
    for entry in _football_player_entries():
        for alias in entry["names"]:
            if _player_name_matches(entity, alias):
                return entry
    return None


def is_top_football_player(name: str) -> bool:
    """True when player is on the curated European top-league list."""
    return _find_football_player_entry(name) is not None


def top_football_player_profile(name: str) -> Optional[dict]:
    """Public profile fields for admin UI / auto-import."""
    entry = _find_football_player_entry(name)
    if entry is None:
        return None
    return {
        "displayName": entry["displayName"],
        "team": entry["team"],
        "league": entry["league"],
    }
