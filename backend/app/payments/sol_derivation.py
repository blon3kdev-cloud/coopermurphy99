"""Solana HD derivation — Exodus-compatible paths via solders + bip-utils."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from bip_utils import Bip39SeedGenerator, Bip44, Bip44Changes, Bip44Coins
from solders.keypair import Keypair

from ..config import get_settings

log = logging.getLogger(__name__)

_DEFAULT_SOLDERS_TEMPLATE = "m/44'/501'/{account}'/0/{index}"

_EXODUS_TEMPLATES = (
    "m/44'/501'/{account}'/0/{index}",
    "m/44/501/{account}/0/{index}",
    "m/44'/501'/{account}'/0'/{index}'",
    "m/44'/501'/{account}'/1/{index}",
)


@dataclass(frozen=True)
class SolDerivationProfile:
    kind: str  # "solders" | "bip44" | "bip44_change"
    path_template: Optional[str] = None
    account: int = 0
    base_index: int = 0  # path index that maps to derive_solana_address(0)


_profile: Optional[SolDerivationProfile] = None


def _seed_bytes() -> bytes:
    settings = get_settings()
    mnemonic = settings.payment_wallet_mnemonic.strip()
    if not mnemonic:
        raise RuntimeError("PAYMENT_WALLET_MNEMONIC is not set")
    passphrase = settings.payment_wallet_passphrase or ""
    return Bip39SeedGenerator(mnemonic).Generate(passphrase)


def _solders_address(seed: bytes, path: str) -> str:
    kp = Keypair.from_seed_and_derivation_path(seed, path)
    return str(kp.pubkey())


def _bip44_address_index(seed: bytes, index: int, account: int = 0) -> str:
    ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
    return (
        ctx.Purpose()
        .Coin()
        .Account(account)
        .Change(Bip44Changes.CHAIN_EXT)
        .AddressIndex(index)
        .PublicKey()
        .ToAddress()
    )


def _bip44_change_level(seed: bytes, account: int = 0) -> str:
    """Exodus-style: address at change level without AddressIndex (m/44'/501'/0'/0')."""
    ctx = Bip44.FromSeed(seed, Bip44Coins.SOLANA)
    return (
        ctx.Purpose()
        .Coin()
        .Account(account)
        .Change(Bip44Changes.CHAIN_EXT)
        .PublicKey()
        .ToAddress()
    )


def get_sol_profile() -> SolDerivationProfile:
    if _profile is None:
        raise RuntimeError(
            "Solana profile not resolved; call ensure_solana_profile() first"
        )
    return _profile


def ensure_solana_profile(expected_master: str = "") -> SolDerivationProfile:
    """
    Resolve Exodus-style path when MASTER matches mnemonic; otherwise use the
    default solders path so deposit addresses stay deterministic from the seed.
    """
    global _profile
    if _profile is not None:
        return _profile

    expected = expected_master.strip()
    if expected:
        try:
            return resolve_solana_profile(expected)
        except RuntimeError:
            log.warning(
                "MASTER_SOLANA_ADDRESS %s does not match PAYMENT_WALLET_MNEMONIC; "
                "deposit addresses use %s. Sweeps still send to the configured master.",
                expected,
                _DEFAULT_SOLDERS_TEMPLATE,
            )

    _profile = SolDerivationProfile(
        "solders", _DEFAULT_SOLDERS_TEMPLATE, account=0, base_index=0
    )
    return _profile


def derive_solana_address(derivation_index: int) -> str:
    """Map payment derivation_index so index 0 == MASTER (base_index on path)."""
    if _profile is None:
        ensure_solana_profile(get_settings().master_solana_address.strip())
    profile = get_sol_profile()
    seed = _seed_bytes()
    path_index = profile.base_index + derivation_index

    if profile.kind == "solders" and profile.path_template:
        path = profile.path_template.format(account=profile.account, index=path_index)
        return _solders_address(seed, path)
    if profile.kind == "bip44_change":
        if derivation_index != 0:
            # change-level has no further indices; use solders increment from same base path
            path = f"m/44'/501'/{profile.account}'/0/{path_index}"
            return _solders_address(seed, path)
        return _bip44_change_level(seed, profile.account)
    return _bip44_address_index(seed, path_index, profile.account)


def iter_candidate_addresses(seed: bytes, max_account: int = 3, max_index: int = 30) -> list[tuple[str, str]]:
    """List (label, address) for debugging — used by discover script."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add(label: str, addr: str) -> None:
        if addr not in seen:
            seen.add(addr)
            out.append((label, addr))

    for account in range(max_account + 1):
        try:
            add(f"bip44_change account={account}", _bip44_change_level(seed, account))
        except Exception:
            pass
        for tpl in _EXODUS_TEMPLATES:
            if "{index}" not in tpl:
                continue
            for index in range(max_index + 1):
                path = tpl.format(account=account, index=index)
                try:
                    add(f"solders {path}", _solders_address(seed, path))
                except Exception:
                    pass
        for index in range(max_index + 1):
            try:
                add(
                    f"bip44 m/44'/501'/{account}'/0'/{index}",
                    _bip44_address_index(seed, index, account),
                )
            except Exception:
                pass
    return out


def resolve_solana_profile(expected_master: str) -> SolDerivationProfile:
    """Find derivation where derive_solana_address(0) == expected_master."""
    global _profile
    expected = expected_master.strip()
    if not expected:
        raise RuntimeError("MASTER_SOLANA_ADDRESS is empty")

    seed = _seed_bytes()
    settings = get_settings()
    custom = (settings.solana_derivation_path or "").strip()

    if custom:
        tpl = custom if "{index}" in custom else f"{custom.rstrip('/')}/{{index}}"
        path0 = tpl.format(account=0, index=0) if "{account}" in tpl else tpl.format(index=0)
        addr = _solders_address(seed, path0)
        if addr != expected:
            raise RuntimeError(
                f"SOLANA_DERIVATION_PATH does not match MASTER_SOLANA_ADDRESS. "
                f"Path {path0} -> {addr}, expected {expected}"
            )
        _profile = SolDerivationProfile("solders", tpl, account=0, base_index=0)
        return _profile

    for account in range(8):
        # Exodus legacy: pubkey at change level (no /0 index)
        try:
            if _bip44_change_level(seed, account) == expected:
                _profile = SolDerivationProfile("bip44_change", account=account, base_index=0)
                return _profile
        except Exception:
            pass

        for tpl in _EXODUS_TEMPLATES:
            if "{index}" not in tpl:
                continue
            for index in range(80):
                path = tpl.format(account=account, index=index)
                try:
                    if _solders_address(seed, path) == expected:
                        _profile = SolDerivationProfile(
                            "solders", tpl, account=account, base_index=index
                        )
                        return _profile
                except Exception:
                    continue

        for index in range(80):
            try:
                if _bip44_address_index(seed, index, account) == expected:
                    _profile = SolDerivationProfile(
                        "bip44", account=account, base_index=index
                    )
                    return _profile
            except Exception:
                continue

    exodus0 = _solders_address(seed, "m/44'/501'/0'/0/0")
    change0 = _bip44_change_level(seed, 0)
    raise RuntimeError(
        "MASTER_SOLANA_ADDRESS does not match this mnemonic on any tested path (0–79 indices, "
        "accounts 0–7, Exodus + bip44 + change-level). "
        f"Mnemonic produces m/44'/501'/0'/0/0 -> {exodus0} and change-level -> {change0}. "
        f"Exodus UI shows -> {expected}. "
        "Usually the recovery phrase in PAYMENT_WALLET_MNEMONIC is not the same backup as the "
        "wallet that owns that address (wrong words, extra passphrase, or imported key in Exodus). "
        "Run: npm run discover-solana — to list addresses this mnemonic generates."
    )


def reset_sol_profile() -> None:
    """Clear cached profile (tests)."""
    global _profile
    _profile = None
