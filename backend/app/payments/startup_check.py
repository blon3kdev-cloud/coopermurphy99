"""Verify MASTER_* env addresses match mnemonic index-0 derivation."""
from __future__ import annotations

import hmac
import logging
import re

from ..config import get_settings
from .derivation import derive_address, master_addresses
from .types import PaymentAsset

log = logging.getLogger(__name__)

_SOLANA_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def _eq_eth_btc(a: str, b: str) -> bool:
    return hmac.compare_digest(a.strip().lower(), b.strip().lower())


def _eq_solana(a: str, b: str) -> bool:
    return hmac.compare_digest(a.strip(), b.strip())


def verify_master_addresses() -> None:
    """Raise RuntimeError if required masters are missing or mismatch derivation."""
    settings = get_settings()
    if not settings.payments_enabled:
        raise RuntimeError(
            "PAYMENT_WALLET_MNEMONIC is required for crypto payments"
        )

    checks: list[tuple[str, str]] = [
        ("MASTER_BTC_ADDRESS", settings.master_btc_address),
        ("MASTER_ETH_ADDRESS", settings.master_eth_address),
    ]
    if settings.payments_solana_enabled:
        from .sol_derivation import ensure_solana_profile

        master_sol = settings.master_solana_address.strip()
        if not master_sol or not _SOLANA_RE.match(master_sol):
            raise RuntimeError(
                "MASTER_SOLANA_ADDRESS must be a valid base58 Solana address"
            )
        ensure_solana_profile(master_sol)
        checks.append(("MASTER_SOLANA_ADDRESS", settings.master_solana_address))

        usdc_eth = settings.master_usdc_eth
        usdc_sol = settings.master_usdc_solana
        if not usdc_eth:
            raise RuntimeError(
                "Set MASTER_USDC_ETH_ADDRESS or MASTER_ETH_ADDRESS for USDC (Ethereum)"
            )
        if not usdc_sol:
            raise RuntimeError(
                "Set MASTER_USDC_SOLANA_ADDRESS or MASTER_SOLANA_ADDRESS for USDC (Solana)"
            )
        derived_usdc_eth = derive_address(PaymentAsset.USDC_ETH, 0)
        if not _eq_eth_btc(usdc_eth, derived_usdc_eth):
            raise RuntimeError(
                "MASTER_USDC_ETH_ADDRESS must match the ETH deposit address at index 0 "
                f"(expected {derived_usdc_eth}, got {usdc_eth})"
            )
        derived_sol0 = derive_address(PaymentAsset.SOL, 0)
        if not _eq_solana(usdc_sol, derived_sol0) and not _eq_solana(
            usdc_sol, master_sol
        ):
            log.warning(
                "MASTER_USDC_SOLANA_ADDRESS differs from HD index-0 (%s); "
                "using it only as sweep destination",
                derived_sol0,
            )

    missing = [name for name, expected in checks if not expected.strip()]
    if missing:
        raise RuntimeError(
            f"Missing required env vars: {', '.join(missing)}"
        )

    derived = master_addresses()
    for name, expected in checks:
        key = name.replace("MASTER_", "").replace("_ADDRESS", "").lower()
        if key == "solana":
            key = "sol"
        if key not in derived:
            continue
        actual = derived[key]
        eq = _eq_solana if key == "sol" else _eq_eth_btc
        if not eq(expected, actual):
            if key == "sol":
                log.warning(
                    "%s (%s) differs from mnemonic index-0 (%s); "
                    "deposits use derived addresses, sweeps use the configured master",
                    name,
                    expected.strip(),
                    actual,
                )
                continue
            raise RuntimeError(
                f"{name} does not match address derived from PAYMENT_WALLET_MNEMONIC "
                f"(index 0). Expected {expected.strip()}, got {actual}"
            )
