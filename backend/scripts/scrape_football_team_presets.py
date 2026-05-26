#!/usr/bin/env python3
"""Fetch club crests and create MongoDB presets from top_football_teams.json.

Uses Wikipedia's public API (direct page lookup, then search fallback), then stores
images as data URLs like the admin Presets UI.

Usage (from backend/):
  .venv/bin/python scripts/scrape_football_team_presets.py
  .venv/bin/python scripts/scrape_football_team_presets.py --replace --delay 2
  .venv/bin/python scripts/scrape_football_team_presets.py --dry-run --team "Arsenal"
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from preset_scraper_lib import (  # noqa: E402
    fetch_image_url,
    load_named_entries,
    norm,
    pick_title_by_score,
    print_summary,
    run_scraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s | %(message)s",
)
log = logging.getLogger("football_team_presets")

_TEAMS_FILE = _ROOT / "data" / "top_football_teams.json"
_IMAGE_DIR = _ROOT / "data" / "football_team_preset_images"
_DEFAULT_DELAY = 2.0

_FC_SUFFIX_RE = (
    " fc",
    " f.c.",
    " cf",
    " c.f.",
    " sc",
    " s.k.",
    " sk",
)


def load_teams() -> list[dict[str, Any]]:
    return load_named_entries(_TEAMS_FILE, key="teams")


def _title_candidates(team: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(title: str) -> None:
        t = title.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)

    for name in team["names"]:
        add(name)
        lower = norm(name)
        if not any(lower.endswith(s) for s in _FC_SUFFIX_RE):
            add(f"{name} FC")
            add(f"{name} F.C.")
    return out


def _search_queries(team: dict[str, Any]) -> list[str]:
    name = team["preset_name"]
    return [
        f"{name} football club",
        f"{name} FC",
        name,
    ]


def _score_hit(hit: dict[str, str], name_l: str, name_parts: set[str]) -> int:
    title = norm(hit.get("title", ""))
    snippet = norm(hit.get("snippet", ""))
    s = 0
    if title == name_l:
        s += 80
    elif name_l in title or title in name_l:
        s += 50
    if name_parts & set(title.split()):
        s += 20
    for word in (
        "football club",
        "f.c.",
        " fc",
        "association football",
        "soccer club",
        "football team",
    ):
        if word in snippet or word in title:
            s += 10
    for bad in (
        "disambiguation",
        "season",
        "squad",
        "manager",
        "women",
        "youth",
        "academy",
        "reserve",
        "stadium",
        "film",
        "song",
        "national team",
        "u21",
        "u-21",
    ):
        if bad in title or bad in snippet:
            s -= 30
    return s


def _pick_title(results: list[dict[str, str]], primary_name: str) -> Optional[str]:
    return pick_title_by_score(results, primary_name, score_hit=_score_hit)


async def fetch_team_image_url(
    client: httpx.AsyncClient, team: dict[str, Any], pause: Callable[[], Any]
) -> Optional[str]:
    return await fetch_image_url(
        client,
        team,
        title_candidates=_title_candidates(team),
        search_queries=_search_queries(team),
        pick_title=_pick_title,
        pause=pause,
        log=log,
    )


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape football club crests and create presets."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Update existing presets (matched by name aliases) instead of skipping",
    )
    parser.add_argument("--no-skip-existing", action="store_true", help="Alias for --replace")
    parser.add_argument(
        "--no-save-files",
        action="store_true",
        help="Do not write JPEG copies under data/football_team_preset_images/",
    )
    parser.add_argument(
        "--team",
        action="append",
        dest="teams",
        metavar="NAME",
        help="Only process teams whose primary name contains NAME (repeatable)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=_DEFAULT_DELAY,
        help=f"Seconds between teams (default: {_DEFAULT_DELAY})",
    )
    args = parser.parse_args()
    replace = args.replace or args.no_skip_existing

    if not _TEAMS_FILE.is_file():
        log.error("Missing %s", _TEAMS_FILE)
        sys.exit(1)

    teams = load_teams()
    if args.teams:
        filters = [norm(t) for t in args.teams]
        teams = [
            team
            for team in teams
            if any(f in norm(team["preset_name"]) for f in filters)
        ]
    if not teams:
        log.error("No teams matched")
        sys.exit(1)

    results = await run_scraper(
        entities=teams,
        entity_label="team",
        image_dir=_IMAGE_DIR,
        fetch_image=fetch_team_image_url,
        dry_run=args.dry_run,
        replace=replace,
        save_files=not args.no_save_files,
        delay=args.delay,
        log=log,
    )
    print_summary(results, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
