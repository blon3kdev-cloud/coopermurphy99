#!/usr/bin/env python3
"""List Solana addresses derived from PAYMENT_WALLET_MNEMONIC — find Exodus match."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(_ROOT / ".env")

from app.config import get_settings
from app.payments.sol_derivation import _seed_bytes, iter_candidate_addresses


def main() -> None:
    settings = get_settings()
    if not settings.payments_enabled:
        print("Set PAYMENT_WALLET_MNEMONIC in backend/.env")
        sys.exit(1)

    target = (settings.master_solana_address or "").strip()
    seed = _seed_bytes()
    print("Searching derivation paths for your mnemonic...\n")
    if target:
        print(f"Looking for Exodus address: {target}\n")

    found = False
    for label, addr in iter_candidate_addresses(seed, max_account=3, max_index=40):
        mark = ""
        if target and addr == target:
            mark = "  <-- MATCHES MASTER_SOLANA_ADDRESS"
            found = True
        print(f"{label}\n  {addr}{mark}\n")

    if target and not found:
        print(
            "No match in first 40 indices / 3 accounts.\n"
            "Your mnemonic does not generate the Exodus address you configured.\n"
            "Fix: use the exact Exodus backup phrase, or update MASTER_SOLANA_ADDRESS to one listed above."
        )
        sys.exit(1)
    if target and found:
        print("Match found — npm run test-payment should work after restart.")


if __name__ == "__main__":
    main()
