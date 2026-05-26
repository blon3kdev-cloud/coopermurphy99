#!/usr/bin/env python3
"""Pre-flight .env checks before deploy (run from backend root)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def _get(key: str) -> str:
    return os.environ.get(key, "").strip()


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []

    if not (ROOT / ".env").is_file():
        errors.append("backend/.env missing — copy from .env.example and fill in values")

    if not _get("DATABASE_URL"):
        errors.append("DATABASE_URL is required in backend/.env")

    secret = _get("INTERNAL_SECRET")
    if not secret:
        errors.append("INTERNAL_SECRET is required in backend/.env")
    elif secret == "change-me-to-32-random-bytes-min":
        warnings.append("INTERNAL_SECRET is still the .env.example placeholder")

    if not _get("DISCORD_TOKEN"):
        warnings.append("DISCORD_TOKEN unset — Discord bot will not start")
    if not _get("TELEGRAM_TOKEN"):
        warnings.append("TELEGRAM_TOKEN unset — Telegram bot will not start")

    if not errors:
        try:
            from app.config import get_settings
            from app.safe_url import validate_production_secrets

            get_settings.cache_clear()
            get_settings()
            validate_production_secrets()
        except Exception as exc:
            errors.append(str(exc))

    for msg in warnings:
        print(f"WARN: {msg}")
    for msg in errors:
        print(f"ERROR: {msg}", file=sys.stderr)

    if errors:
        return 1
    print("Backend env check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
