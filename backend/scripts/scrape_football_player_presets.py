#!/usr/bin/env python3
"""Fetch player headshots and create MongoDB presets from top_football_players.json.

Uses Wikipedia's public API (direct page lookup, then search fallback), then stores
images as data URLs like the admin Presets UI.

Usage (from backend/):
  .venv/bin/python scripts/scrape_football_player_presets.py
  .venv/bin/python scripts/scrape_football_player_presets.py --replace --delay 2
  .venv/bin/python scripts/scrape_football_player_presets.py --dry-run --player "Bruno Fernandes"
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
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
    norm,
    pick_title_by_score,
    print_summary,
    run_scraper,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s | %(message)s",
)
log = logging.getLogger("player_presets")

_PLAYERS_FILE = _ROOT / "data" / "top_football_players.json"
_IMAGE_DIR = _ROOT / "data" / "player_preset_images"
_DEFAULT_DELAY = 2.0


def load_players() -> list[dict[str, Any]]:
    raw = json.loads(_PLAYERS_FILE.read_text(encoding="utf-8"))
    out: list[dict[str, Any]] = []
    for entry in raw.get("players", []):
        names = [str(n).strip() for n in entry.get("names", []) if str(n).strip()]
        if not names:
            continue
        out.append(
            {
                "preset_name": names[0],
                "names": names,
                "team": str(entry.get("team", "")).strip(),
                "league": str(entry.get("league", "")).strip(),
            }
        )
    return out


def _title_candidates(player: dict[str, Any]) -> list[str]:
    name = player["preset_name"]
    return [name, f"{name} (footballer)"]


def _search_queries(player: dict[str, Any]) -> list[str]:
    name = player["preset_name"]
    return [f"{name} footballer", name]


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
    if "(footballer)" in title and "born" not in title:
        s += 15
    for word in ("football", "footballer", "soccer", "striker", "midfielder"):
        if word in snippet or word in title:
            s += 8
    for bad in (
        "national team",
        "u21",
        "u-21",
        "women",
        "film",
        "song",
        "disambiguation",
    ):
        if bad in title or bad in snippet:
            s -= 30
    if re.search(r"\bborn\s+(19|20)\d{2}\b", title):
        s -= 50
    return s


def _pick_title(results: list[dict[str, str]], primary_name: str) -> Optional[str]:
    return pick_title_by_score(results, primary_name, score_hit=_score_hit)


async def fetch_player_image_url(
    client: httpx.AsyncClient, player: dict[str, Any], pause: Callable[[], Any]
) -> Optional[str]:
    return await fetch_image_url(
        client,
        player,
        title_candidates=_title_candidates(player),
        search_queries=_search_queries(player),
        pick_title=_pick_title,
        pause=pause,
        log=log,
    )


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape football player photos and create presets."
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
        help="Do not write JPEG copies under data/player_preset_images/",
    )
    parser.add_argument(
        "--player",
        action="append",
        dest="players",
        metavar="NAME",
        help="Only process players whose primary name contains NAME (repeatable)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=_DEFAULT_DELAY,
        help=f"Seconds between players (default: {_DEFAULT_DELAY})",
    )
    args = parser.parse_args()
    replace = args.replace or args.no_skip_existing

    if not _PLAYERS_FILE.is_file():
        log.error("Missing %s", _PLAYERS_FILE)
        sys.exit(1)

    players = load_players()
    if args.players:
        filters = [norm(p) for p in args.players]
        players = [
            pl
            for pl in players
            if any(f in norm(pl["preset_name"]) for f in filters)
        ]
    if not players:
        log.error("No players matched")
        sys.exit(1)

    results = await run_scraper(
        entities=players,
        entity_label="player",
        image_dir=_IMAGE_DIR,
        fetch_image=fetch_player_image_url,
        dry_run=args.dry_run,
        replace=replace,
        save_files=not args.no_save_files,
        delay=args.delay,
        log=log,
    )
    print_summary(results, dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
