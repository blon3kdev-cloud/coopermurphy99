#!/usr/bin/env python3
"""Merge presets and bets (markets) from dev MongoDB into prod.

Usage:
  cd backend
  .venv/bin/python scripts/merge_dev_presets_bets_to_prod.py
  .venv/bin/python scripts/merge_dev_presets_bets_to_prod.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)

from app.db import close_db, get_database, init_db
from app.env_sync import merge_markets, merge_presets

log = logging.getLogger("merge_dev_to_prod")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Merge dev presets and bets into prod")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count documents only; do not write to prod",
    )
    args = parser.parse_args()

    await init_db()
    try:
        dev_db = get_database("dev")
        prod_db = get_database("prod")

        preset_count = await dev_db.presets.count_documents({})
        market_count = await dev_db.markets.count_documents({})
        log.info("dev presets=%s markets=%s", preset_count, market_count)

        if args.dry_run:
            print(
                json.dumps(
                    {
                        "dryRun": True,
                        "wouldMerge": {"presets": preset_count, "markets": market_count},
                    },
                    indent=2,
                )
            )
            return

        presets = await merge_presets(dev_db, prod_db)
        markets = await merge_markets(dev_db, prod_db)
        result = {"presets": presets, "markets": markets}
        print(json.dumps(result, indent=2))
        log.info("Merge complete: %s", result)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
