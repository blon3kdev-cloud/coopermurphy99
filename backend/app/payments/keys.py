"""Private key derivation for signing sweep transactions."""
from __future__ import annotations

from bip_utils import Bip44, Bip44Changes, Bip44Coins, Bip84, Bip84Coins

from .derivation import _btc_ctx, _eth_ctx


def eth_private_key_bytes(derivation_index: int) -> bytes:
    ctx = _eth_ctx()
    return (
        ctx.Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(derivation_index)
        .PrivateKey()
        .Raw()
        .ToBytes()
    )


def btc_private_key_wif(derivation_index: int) -> str:
    ctx = _btc_ctx()
    return (
        ctx.Purpose()
        .Coin()
        .Account(0)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(derivation_index)
        .PrivateKey()
        .ToWif()
    )


def sol_keypair(derivation_index: int):
    """Solders Keypair for the payment derivation index."""
    from solders.keypair import Keypair

    from .sol_derivation import derive_solana_address, get_sol_profile, _seed_bytes

    profile = get_sol_profile()
    seed = _seed_bytes()
    path_index = profile.base_index + derivation_index
    if profile.kind == "solders" and profile.path_template:
        path = profile.path_template.format(
            account=profile.account, index=path_index
        )
        return Keypair.from_seed_and_derivation_path(seed, path)
    # Fallback: derive pubkey path then use index-based solders path
    _ = derive_solana_address(derivation_index)
    path = f"m/44'/501'/{profile.account}'/0/{path_index}"
    return Keypair.from_seed_and_derivation_path(seed, path)
