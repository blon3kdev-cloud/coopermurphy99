#!/usr/bin/env python3
"""One-shot check for a pending crypto payment (e.g. after RPC was down)."""
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
from app.payments.types import PaymentAsset, PaymentKind, PaymentStatus


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: npm run check-payment -- <payment_id>")
        sys.exit(1)

    payment_id = int(sys.argv[1])
    if not get_settings().payments_enabled:
        print("Configure PAYMENT_WALLET_MNEMONIC in .env")
        sys.exit(1)

    verify_master_addresses()
    await init_db()

    try:
        doc = await PaymentService.get_payment(payment_id)
        if not doc:
            print(f"Payment #{payment_id} not found")
            sys.exit(1)

        print(f"Payment #{payment_id} status={doc['status']} asset={doc['asset']}")
        print(f"  Expected: {doc['amount_expected']}")
        print(f"  Address:  {doc['address']}")

        if doc["kind"] != PaymentKind.DEPOSIT.value:
            print("Not a deposit — nothing to watch on-chain.")
            return

        if doc["status"] == PaymentStatus.CONFIRMED.value:
            print("Already confirmed.")
            print(f"  Received: {doc.get('amount_received')}")
            return

        import httpx
        from app.payments.monitors import check_payment_received

        asset = PaymentAsset(doc["asset"])
        async with httpx.AsyncClient() as client:
            result = await check_payment_received(
                client,
                asset,
                doc["address"],
                doc["amount_expected"],
            )

        print(f"  On-chain balance: {result.received}")
        if result.confirmed:
            doc = await PaymentService._confirm(
                payment_id,
                received=result.received,
                tx_ids=result.tx_ids,
                confirmations=result.confirmations,
            )
            print("PAYMENT RECEIVED — marked confirmed in DB.")
            if doc.get("sweep_tx_id"):
                print(f"  Swept to master: {doc['sweep_tx_id']}")
                print(f"  https://etherscan.io/tx/{doc['sweep_tx_id']}")
            elif doc.get("sweep_status") == "failed":
                print(f"  Sweep failed: {doc.get('sweep_error')}")
                print("  Run: npm run sweep-payment --", payment_id)
        else:
            print("Not enough funds yet on this address (or still confirming).")
            if doc["status"] == PaymentStatus.EXPIRED.value:
                print("Note: payment was expired in DB; send again or create a new deposit.")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
