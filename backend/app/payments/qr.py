"""QR code generation for payment addresses (BIP21 / EIP-681)."""
from __future__ import annotations

import io
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import qrcode

from ..config import get_settings
from .types import ASSET_DECIMALS, PaymentAsset


def format_amount(amount: Decimal, asset: PaymentAsset) -> str:
    """Human- and wallet-safe decimal string (never scientific notation)."""
    decimals = ASSET_DECIMALS[asset]
    step = Decimal(10) ** -decimals
    q = amount.quantize(step)
    s = format(q, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def qr_payload(address: str) -> str:
    """QR content — raw address only (max wallet compatibility)."""
    return address.strip()


def payment_uri(asset: PaymentAsset, address: str, amount: Decimal | None = None) -> str:
    """
    Build a URI wallets accept when scanning QR codes.

    BTC: BIP21 bitcoin:<addr>?amount=<decimal BTC>
    ETH: EIP-681 ethereum:<addr>@1?value=<wei>
    USDC (ETH): EIP-681 token transfer on mainnet
    """
    address = address.strip()
    if amount is None or amount <= 0:
        return _address_only_uri(asset, address)

    if asset == PaymentAsset.BTC:
        amt = format_amount(amount, asset)
        return f"bitcoin:{address}?amount={amt}"

    if asset == PaymentAsset.ETH:
        wei = int((amount * Decimal(10**18)).to_integral_value())
        return f"ethereum:{address}@1?value={wei}"

    if asset == PaymentAsset.USDC_ETH:
        settings = get_settings()
        contract = settings.usdc_eth_contract
        units = int((amount * Decimal(10**6)).to_integral_value())
        return (
            f"ethereum:{contract}@1/transfer"
            f"?address={quote(address)}&uint256={units}"
        )

    if asset in (PaymentAsset.SOL, PaymentAsset.USDC_SOL):
        amt = format_amount(amount, asset)
        return f"solana:{address}?amount={amt}&label=payment"

    return address


def _address_only_uri(asset: PaymentAsset, address: str) -> str:
    if asset == PaymentAsset.BTC:
        return f"bitcoin:{address}"
    if asset in (PaymentAsset.ETH, PaymentAsset.USDC_ETH):
        return f"ethereum:{address}@1"
    if asset in (PaymentAsset.SOL, PaymentAsset.USDC_SOL):
        return f"solana:{address}"
    return address


def qr_ascii(data: str) -> str:
    qr = qrcode.QRCode(border=1)
    qr.add_data(data)
    qr.make(fit=True)
    buf = io.StringIO()
    qr.print_ascii(out=buf)
    return buf.getvalue()


def qr_png_bytes(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def save_qr_png(data: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(qr_png_bytes(data))
    return path
