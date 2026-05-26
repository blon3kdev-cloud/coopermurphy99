#!/usr/bin/env python3
"""Daily 00:00 job: auto-import 5 football + 5 NBA iSports markets.

Crontab example (Europe/Warsaw midnight):
  0 0 * * * cd /path/to/backend && .venv/bin/python scripts/daily_isports_auto.py >> logs/daily_isports.log 2>&1
"""
from __future__ import annotations

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

from app.config import get_settings
from app.db import close_db, init_db
from app.isports_daily_auto import run_daily_isports_auto_import


async def main() -> None:
    if not get_settings().isports_api_key.strip():
        print("I_SPORTS_API_KEY not configured — skipping")
        sys.exit(0)

    await init_db()
    try:
        result = await run_daily_isports_auto_import()
        print(json.dumps(result, indent=2, default=str))
        has_errors = any(
            (result.get(key) or {}).get("errors")
            for key in ("football", "basketball")
        )
        if has_errors:
            sys.exit(1)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
