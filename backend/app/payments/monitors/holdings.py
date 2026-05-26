"""Read current on-chain holdings at an address (for deposit/withdraw matching)."""
from __future__ import annotations

from decimal import Decimal

import httpx

from ..types import PaymentAsset
from .btc import check_btc
from .eth import _eth_balance, check_usdc_eth
from .sol import check_sol, check_usdc_sol


async def get_address_holdings(
    client: httpx.AsyncClient,
    asset: PaymentAsset,
    address: str,
) -> Decimal:
    if asset == PaymentAsset.ETH:
        return await _eth_balance(client, address)
    if asset == PaymentAsset.USDC_ETH:
        r = await check_usdc_eth(client, address, Decimal(0))
        return r.received
    if asset == PaymentAsset.BTC:
        r = await check_btc(client, address, Decimal(0))
        return r.received
    if asset == PaymentAsset.SOL:
        r = await check_sol(client, address, Decimal(0))
        return r.received
    if asset == PaymentAsset.USDC_SOL:
        r = await check_usdc_sol(client, address, Decimal(0))
        return r.received
    raise ValueError(f"unsupported asset: {asset}")
