"""Route asset to the correct chain monitor."""
from __future__ import annotations

from decimal import Decimal

import httpx

from ..types import PaymentAsset
from .base import MonitorResult
from .btc import check_btc
from .eth import check_eth, check_usdc_eth
from .holdings import get_address_holdings
from .sol import check_sol, check_usdc_sol


async def check_payment_received(
    client: httpx.AsyncClient,
    asset: PaymentAsset,
    address: str,
    expected: Decimal,
) -> MonitorResult:
    if asset == PaymentAsset.BTC:
        return await check_btc(client, address, expected)
    if asset == PaymentAsset.ETH:
        return await check_eth(client, address, expected)
    if asset == PaymentAsset.USDC_ETH:
        return await check_usdc_eth(client, address, expected)
    if asset == PaymentAsset.SOL:
        return await check_sol(client, address, expected)
    if asset == PaymentAsset.USDC_SOL:
        return await check_usdc_sol(client, address, expected)
    raise ValueError(f"unsupported asset: {asset}")


async def check_payment_delta(
    client: httpx.AsyncClient,
    asset: PaymentAsset,
    address: str,
    baseline: Decimal,
    expected: Decimal,
) -> MonitorResult:
    """Confirm when holdings at address increased by at least expected since baseline."""
    current = await get_address_holdings(client, asset, address)
    delta = current - baseline
    confirmed = delta >= expected
    return MonitorResult(
        received=delta if confirmed else max(delta, Decimal(0)),
        confirmed=confirmed,
        tx_ids=[],
        confirmations=1 if confirmed else 0,
    )
