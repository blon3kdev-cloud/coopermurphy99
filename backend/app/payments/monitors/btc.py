"""Bitcoin mainnet monitor via Blockstream API."""
from __future__ import annotations

from decimal import Decimal

import httpx

from .base import MonitorResult

BLOCKSTREAM = "https://blockstream.info/api"
SATOSHI = Decimal("100000000")


async def check_btc(
    client: httpx.AsyncClient, address: str, expected: Decimal
) -> MonitorResult:
    r = await client.get(f"{BLOCKSTREAM}/address/{address}/txs", timeout=30)
    r.raise_for_status()
    txs = r.json()

    received = Decimal(0)
    tx_ids: list[str] = []
    has_confirmed_inflow = False

    for tx in txs:
        status = tx.get("status") or {}
        if not status.get("confirmed"):
            continue
        has_confirmed_inflow = True
        for vout in tx.get("vout", []):
            if vout.get("scriptpubkey_address") != address:
                continue
            value_sat = Decimal(str(vout.get("value", 0)))
            received += value_sat / SATOSHI
            if tx.get("txid"):
                tx_ids.append(tx["txid"])

    confirmed = has_confirmed_inflow and received >= expected
    return MonitorResult(
        received=received,
        confirmed=confirmed,
        tx_ids=list(dict.fromkeys(tx_ids)),
        confirmations=1 if confirmed else 0,
    )
