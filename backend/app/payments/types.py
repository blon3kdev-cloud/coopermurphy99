"""Payment enums and asset metadata."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum


class PaymentKind(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"


class PaymentAsset(str, Enum):
    BTC = "btc"
    ETH = "eth"
    SOL = "sol"
    USDC_ETH = "usdc_eth"
    USDC_SOL = "usdc_sol"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    EXPIRED = "expired"
    FAILED = "failed"
    REFUNDED = "refunded"


ASSET_LABELS: dict[PaymentAsset, str] = {
    PaymentAsset.BTC: "Bitcoin",
    PaymentAsset.ETH: "Ethereum",
    PaymentAsset.SOL: "Solana",
    PaymentAsset.USDC_ETH: "USDC (Ethereum)",
    PaymentAsset.USDC_SOL: "USDC (Solana)",
}

ASSET_SYMBOLS: dict[PaymentAsset, str] = {
    PaymentAsset.BTC: "BTC",
    PaymentAsset.ETH: "ETH",
    PaymentAsset.SOL: "SOL",
    PaymentAsset.USDC_ETH: "USDC",
    PaymentAsset.USDC_SOL: "USDC",
}

# Max decimal places per asset for amount input validation
ASSET_DECIMALS: dict[PaymentAsset, int] = {
    PaymentAsset.BTC: 8,
    PaymentAsset.ETH: 18,
    PaymentAsset.SOL: 9,
    PaymentAsset.USDC_ETH: 6,
    PaymentAsset.USDC_SOL: 6,
}


def asset_enabled(asset: PaymentAsset) -> bool:
    from ..config import get_settings

    settings = get_settings()
    if asset in (PaymentAsset.SOL, PaymentAsset.USDC_SOL):
        return settings.payments_solana_enabled
    return True


def require_asset_enabled(asset: PaymentAsset) -> None:
    if not asset_enabled(asset):
        raise ValueError(
            "Solana payments are disabled. Set PAYMENTS_ENABLE_SOLANA=true and "
            "configure MASTER_SOLANA_ADDRESS when ready."
        )


def parse_amount(asset: PaymentAsset, raw: str) -> Decimal:
    value = Decimal(raw.strip())
    if value <= 0:
        raise ValueError("amount must be positive")
    decimals = ASSET_DECIMALS[asset]
    exp = value.as_tuple().exponent
    if isinstance(exp, int) and -exp > decimals:
        raise ValueError(f"too many decimal places (max {decimals})")
    return value
