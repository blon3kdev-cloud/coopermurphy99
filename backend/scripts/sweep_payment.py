#!/usr/bin/env python3
"""Manually sweep a confirmed deposit to your master wallet."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from app.config import get_settings
from app.db import close_db, init_db
from app.payments import verify_master_addresses
from app.payments.service import PaymentService
from app.payments.types import PaymentKind


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: npm run sweep-payment -- <payment_id>")
        sys.exit(1)

    payment_id = int(sys.argv[1])
    verify_master_addresses()
    await init_db()

    try:
        doc = await PaymentService.get_payment(payment_id)
        if not doc:
            print(f"Payment #{payment_id} not found")
            sys.exit(1)
        if doc["kind"] != PaymentKind.DEPOSIT.value:
            print("Not a deposit")
            sys.exit(1)

        print(f"Payment #{payment_id} status={doc['status']} asset={doc['asset']}")
        print(f"  From: {doc['address']}")
        settings = get_settings()
        asset = doc["asset"]
        masters = {
            "btc": settings.master_btc_address,
            "eth": settings.master_eth_address,
            "usdc_eth": settings.master_usdc_eth,
            "sol": settings.master_solana_address,
            "usdc_sol": settings.master_usdc_solana,
        }
        if asset in masters:
            print(f"  To master: {masters[asset]}")

        if doc.get("sweep_status") == "completed" and doc.get("sweep_tx_id"):
            print(f"Already swept: {doc['sweep_tx_id']}")
            return

        await PaymentService.maybe_sweep_deposit(doc)
        doc = await PaymentService.get_payment(payment_id) or doc
        tx = doc.get("sweep_tx_id")
        if tx:
            print(f"Sweep submitted: {tx}")
            if doc["asset"] in ("eth", "usdc_eth"):
                print(f"https://etherscan.io/tx/{tx}")
            elif doc["asset"] == "btc":
                print(f"https://mempool.space/tx/{tx}")
            elif doc["asset"] in ("sol", "usdc_sol"):
                print(f"https://solscan.io/tx/{tx}")
        elif doc.get("sweep_status") == "waiting":
            print(f"Waiting for more funds on deposit address: {doc.get('sweep_error')}")
        else:
            print(f"Sweep not done: status={doc.get('sweep_status')} {doc.get('sweep_error')}")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
