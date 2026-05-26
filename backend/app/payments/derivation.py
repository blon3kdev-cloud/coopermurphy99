"""HD address derivation from BIP39 mnemonic (mainnet)."""
from __future__ import annotations

from functools import lru_cache

from bip_utils import Bip39SeedGenerator, Bip44, Bip44Changes, Bip44Coins, Bip84, Bip84Coins

from ..config import get_settings
from .types import PaymentAsset


def _seed_bytes() -> bytes:
    settings = get_settings()
    mnemonic = settings.payment_wallet_mnemonic.strip()
    if not mnemonic:
        raise RuntimeError("PAYMENT_WALLET_MNEMONIC is not set")
    return Bip39SeedGenerator(mnemonic).Generate(settings.payment_wallet_passphrase or "")


@lru_cache(maxsize=1)
def _btc_ctx():
    return Bip84.FromSeed(_seed_bytes(), Bip84Coins.BITCOIN)


@lru_cache(maxsize=1)
def _eth_ctx():
    return Bip44.FromSeed(_seed_bytes(), Bip44Coins.ETHEREUM)


def derive_address(asset: PaymentAsset, index: int) -> str:
    """Derive a unique receive address for the given asset and derivation index."""
    if index < 0:
        raise ValueError("derivation index must be non-negative")

    if asset == PaymentAsset.BTC:
        ctx = _btc_ctx()
        return (
            ctx.Purpose()
            .Coin()
            .Account(0)
            .Change(Bip44Changes.CHAIN_EXT)
            .AddressIndex(index)
            .PublicKey()
            .ToAddress()
        )

    if asset in (PaymentAsset.ETH, PaymentAsset.USDC_ETH):
        ctx = _eth_ctx()
        return (
            ctx.Purpose()
            .Coin()
            .Account(0)
            .Change(Bip44Changes.CHAIN_EXT)
            .AddressIndex(index)
            .PublicKey()
            .ToAddress()
        )

    if asset in (PaymentAsset.SOL, PaymentAsset.USDC_SOL):
        if not get_settings().payments_solana_enabled:
            raise ValueError("Solana payments are disabled (PAYMENTS_ENABLE_SOLANA=false)")
        from .sol_derivation import derive_solana_address

        return derive_solana_address(index)

    raise ValueError(f"unsupported asset: {asset}")


def master_addresses() -> dict[str, str]:
    """Index-0 addresses used to verify mnemonic matches env MASTER_* values."""
    out = {
        "btc": derive_address(PaymentAsset.BTC, 0),
        "eth": derive_address(PaymentAsset.ETH, 0),
    }
    if get_settings().payments_solana_enabled:
        from .sol_derivation import ensure_solana_profile

        ensure_solana_profile(get_settings().master_solana_address.strip())
        out["sol"] = derive_address(PaymentAsset.SOL, 0)
    return out
