#!/usr/bin/env python3
"""Smoke-test crypto deposit address generation for all enabled assets."""
from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from app.config import get_settings
from app.db import close_db, init_db
from app.payments import verify_master_addresses
from app.payments.service import PaymentService
from app.payments.types import ASSET_LABELS, PaymentAsset, asset_enabled, require_asset_enabled


async def main() -> None:
    settings = get_settings()
    if not settings.payments_enabled:
        print("FAIL: PAYMENT_WALLET_MNEMONIC not set")
        sys.exit(1)

    try:
        verify_master_addresses()
        print("OK: master address verification passed")
    except Exception as e:
        print(f"FAIL: verify_master_addresses — {e}")
        sys.exit(1)

    await init_db()
    try:
        for asset in PaymentAsset:
            if not asset_enabled(asset):
                print(f"SKIP: {ASSET_LABELS[asset]} (disabled)")
                continue
            require_asset_enabled(asset)
            doc = await PaymentService.create_deposit(
                asset, Decimal("1"), user_id=None, amount_pln=Decimal("10")
            )
            print(
                f"OK: {ASSET_LABELS[asset]:20} id={doc['id']} "
                f"address={doc['address'][:20]}…"
            )
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
