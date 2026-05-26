"""Solana mainnet monitor — native SOL and SPL USDC."""
from __future__ import annotations

from decimal import Decimal

import httpx

from ...config import get_settings
from .base import MonitorResult

LAMPORTS = Decimal("1000000000")
USDC_DECIMALS = Decimal("1000000")


async def _rpc(client: httpx.AsyncClient, method: str, params: list) -> dict:
    settings = get_settings()
    r = await client.post(
        settings.solana_rpc_url,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30,
    )
    r.raise_for_status()
    body = r.json()
    if "error" in body:
        raise RuntimeError(body["error"])
    return body["result"]


async def check_sol(
    client: httpx.AsyncClient, address: str, expected: Decimal
) -> MonitorResult:
    result = await _rpc(client, "getBalance", [address, {"commitment": "confirmed"}])
    lamports = Decimal(str(result.get("value", 0)))
    received = lamports / LAMPORTS
    confirmed = received >= expected
    return MonitorResult(
        received=received,
        confirmed=confirmed,
        tx_ids=[],
        confirmations=1 if confirmed else 0,
    )


async def check_usdc_sol(
    client: httpx.AsyncClient, address: str, expected: Decimal
) -> MonitorResult:
    settings = get_settings()
    mint = settings.usdc_solana_mint
    result = await _rpc(
        client,
        "getTokenAccountsByOwner",
        [
            address,
            {"mint": mint},
            {"encoding": "jsonParsed", "commitment": "confirmed"},
        ],
    )
    received = Decimal(0)
    for item in result.get("value") or []:
        info = (item.get("account") or {}).get("data") or {}
        parsed = info.get("parsed") or {}
        token_amount = (parsed.get("info") or {}).get("tokenAmount") or {}
        ui = token_amount.get("uiAmountString") or token_amount.get("uiAmount") or 0
        received += Decimal(str(ui))

    confirmed = received >= expected
    return MonitorResult(
        received=received,
        confirmed=confirmed,
        tx_ids=[],
        confirmations=1 if confirmed else 0,
    )
