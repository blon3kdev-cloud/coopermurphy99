#!/usr/bin/env python3
"""Interactive terminal flow for crypto deposit/withdraw testing."""
from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path

# backend/ on path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from app.config import get_settings
from app.db import close_db, init_db
from app.payments import verify_master_addresses
from app.payments.qr import qr_payload, save_qr_png
from app.payments.service import PaymentService
from app.payments.types import (
    ASSET_LABELS,
    ASSET_SYMBOLS,
    PaymentAsset,
    PaymentKind,
    PaymentStatus,
    parse_amount,
    require_asset_enabled,
)


def _prompt(label: str) -> str:
    return input(f"{label}: ").strip()


def _choose_kind() -> PaymentKind:
    print("\n1) Deposit\n2) Withdraw")
    while True:
        c = _prompt("Choose (1/2)").lower()
        if c in ("1", "deposit", "d"):
            return PaymentKind.DEPOSIT
        if c in ("2", "withdraw", "w"):
            return PaymentKind.WITHDRAW
        print("Invalid choice.")


def _choose_asset() -> PaymentAsset:
    sol_on = get_settings().payments_solana_enabled
    print("\n1) Bitcoin\n2) Ethereum\n3) USDC (Ethereum)")
    if sol_on:
        print("4) Solana\n5) USDC (Solana)")
    while True:
        c = _prompt("Choose asset").lower()
        if c in ("1", "btc", "bitcoin"):
            return PaymentAsset.BTC
        if c in ("2", "eth", "ethereum"):
            return PaymentAsset.ETH
        if c in ("3", "usdc", "usdc_eth") or (not sol_on and c in ("4",)):
            return PaymentAsset.USDC_ETH
        if sol_on and c in ("4", "sol", "solana"):
            return PaymentAsset.SOL
        if sol_on and c in ("5", "usdc_sol"):
            return PaymentAsset.USDC_SOL
        print("Invalid choice.")


async def _run_deposit(asset: PaymentAsset, amount: Decimal) -> None:
    doc = await PaymentService.create_deposit(asset, amount)
    symbol = ASSET_SYMBOLS[asset]
    qr_path = _ROOT / "tmp" / f"payment_{doc['id']}_qr.png"
    save_qr_png(qr_payload(doc["address"]), qr_path)
    print(PaymentService.format_deposit_instructions(doc, str(qr_path)))
    print("\nWatching blockchain (Ctrl+C to abort)...\n")

    def on_poll(received: Decimal, expected: Decimal) -> None:
        print(f"  … received so far: {received} / {expected} {symbol}")

    try:
        final = await PaymentService.watch_payment(doc["id"], on_poll=on_poll)
    except KeyboardInterrupt:
        print("\nStopped watching. Payment remains pending in DB.")
        return

    _print_result(final, symbol)


async def _run_withdraw(asset: PaymentAsset, amount: Decimal) -> None:
    dest = _prompt("Destination wallet address")
    if not dest:
        print("Address required.")
        return
    doc = await PaymentService.create_withdraw(asset, amount, dest)
    print(
        f"\nWithdraw request #{doc['id']} recorded (status=pending).\n"
        f"Send {amount} {ASSET_SYMBOLS[asset]} to {dest} manually from your master wallet.\n"
        "Automatic outbound transfers are not enabled in this MVP.\n"
    )


def _print_result(doc: dict, symbol: str) -> None:
    status = doc.get("status")
    if status == PaymentStatus.CONFIRMED.value:
        print("PAYMENT RECEIVED")
        print(f"  Amount:  {doc.get('amount_received')} {symbol}")
        if doc.get("tx_ids"):
            print(f"  Tx IDs:  {', '.join(doc['tx_ids'])}")
    elif status == PaymentStatus.EXPIRED.value:
        print("PAYMENT NOT RECEIVED (timeout)")
        print(f"  Expected: {doc.get('amount_expected')} {symbol}")
        print(f"  Address:  {doc.get('address')}")
    else:
        print(f"PAYMENT status: {status}")


async def main() -> None:
    settings = get_settings()
    if not settings.payments_enabled:
        print("Set PAYMENT_WALLET_MNEMONIC, MASTER_BTC_ADDRESS, MASTER_ETH_ADDRESS in backend/.env")
        sys.exit(1)

    verify_master_addresses()
    await init_db()

    try:
        print("=== Crypto payment test (mainnet) — BTC & ETH ===")
        kind = _choose_kind()
        asset = _choose_asset()
        try:
            require_asset_enabled(asset)
        except ValueError as e:
            print(e)
            sys.exit(1)
        raw_amount = _prompt(f"Amount ({ASSET_LABELS[asset]})")
        try:
            amount = parse_amount(asset, raw_amount)
        except ValueError as e:
            print(f"Invalid amount: {e}")
            sys.exit(1)

        if kind == PaymentKind.DEPOSIT:
            await _run_deposit(asset, amount)
        else:
            await _run_withdraw(asset, amount)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
