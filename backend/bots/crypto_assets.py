"""Crypto asset menus for Discord / Telegram (deposit & withdraw)."""
from __future__ import annotations

from app.payments.types import ASSET_LABELS, ASSET_SYMBOLS, PaymentAsset, asset_enabled

USDC_CHOICE = "usdc"


def solana_payments_on() -> bool:
    return asset_enabled(PaymentAsset.SOL)


def deposit_menu_items() -> list[tuple[str, str, str]]:
    """(label, picker_value, description) for asset select."""
    items: list[tuple[str, str, str]] = [
        (ASSET_LABELS[PaymentAsset.BTC], PaymentAsset.BTC.value, ASSET_SYMBOLS[PaymentAsset.BTC]),
        (ASSET_LABELS[PaymentAsset.ETH], PaymentAsset.ETH.value, ASSET_SYMBOLS[PaymentAsset.ETH]),
    ]
    if solana_payments_on():
        items.append(
            (
                ASSET_LABELS[PaymentAsset.SOL],
                PaymentAsset.SOL.value,
                ASSET_SYMBOLS[PaymentAsset.SOL],
            )
        )
    items.append(("USDC", USDC_CHOICE, "Pick Ethereum or Solana network next"))
    return items


def withdraw_menu_items() -> list[tuple[str, str, str]]:
    return deposit_menu_items()


def is_usdc_choice(value: str) -> bool:
    return value.strip().lower() == USDC_CHOICE


def resolve_asset_choice(value: str) -> PaymentAsset:
    v = value.strip().lower()
    if is_usdc_choice(v):
        raise ValueError("USDC requires network selection")
    return PaymentAsset(v)


def resolve_usdc_network(network: str) -> PaymentAsset:
    n = network.strip().lower()
    if n in ("eth", "ethereum", "usdc_eth", "erc20"):
        return PaymentAsset.USDC_ETH
    if n in ("sol", "solana", "usdc_sol", "spl"):
        if not solana_payments_on():
            raise ValueError("USDC on Solana is not enabled")
        return PaymentAsset.USDC_SOL
    raise ValueError(f"Unknown USDC network: {network}")


def usdc_network_options() -> list[tuple[str, str]]:
    """(label, picker_value) for the USDC network step."""
    opts = [("Ethereum (ERC-20)", "eth")]
    if solana_payments_on():
        opts.append(("Solana (SPL)", "sol"))
    return opts
