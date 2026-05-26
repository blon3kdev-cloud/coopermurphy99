"""Ethereum mainnet monitor — native ETH and ERC-20 USDC."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

import httpx

from ...config import get_settings
from .base import MonitorResult

log = logging.getLogger(__name__)

WEI = Decimal("1000000000000000000")
USDC_DECIMALS = Decimal("1000000")

# Public mainnet RPCs (tried in order after ETH_RPC_URL)
_ETH_RPC_FALLBACKS = (
    "https://ethereum.publicnode.com",
    "https://rpc.ankr.com/eth",
    "https://cloudflare-eth.com",
    "https://1rpc.io/eth",
    "https://eth.drpc.org",
)


def _pad_address(addr: str) -> str:
    return addr.lower().replace("0x", "").zfill(64)


def _eth_rpc_urls() -> list[str]:
    settings = get_settings()
    urls: list[str] = []
    primary = (settings.eth_rpc_url or "").strip()
    if primary:
        urls.append(primary)
    for u in _ETH_RPC_FALLBACKS:
        if u not in urls:
            urls.append(u)
    return urls


async def _rpc(client: httpx.AsyncClient, method: str, params: list) -> str:
    last_err: Optional[Exception] = None
    for url in _eth_rpc_urls():
        try:
            r = await client.post(
                url,
                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                timeout=25,
            )
            r.raise_for_status()
            body = r.json()
            if "error" in body:
                raise RuntimeError(body["error"])
            return body["result"]
        except Exception as e:
            last_err = e
            log.debug("eth rpc %s failed: %s", url, e)
            continue
    raise RuntimeError(f"all ETH RPC endpoints failed: {last_err}")


async def _etherscan_balance_wei(
    client: httpx.AsyncClient, address: str
) -> Optional[Decimal]:
    settings = get_settings()
    api_key = (settings.etherscan_api_key or "").strip()
    if not api_key:
        return None
    r = await client.get(
        "https://api.etherscan.io/api",
        params={
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": api_key,
        },
        timeout=25,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "1":
        return None
    return Decimal(str(data["result"])) / WEI


async def _etherscan_usdc_balance(
    client: httpx.AsyncClient, address: str
) -> Optional[Decimal]:
    settings = get_settings()
    api_key = (settings.etherscan_api_key or "").strip()
    if not api_key:
        return None
    r = await client.get(
        "https://api.etherscan.io/api",
        params={
            "module": "account",
            "action": "tokenbalance",
            "contractaddress": settings.usdc_eth_contract,
            "address": address,
            "tag": "latest",
            "apikey": api_key,
        },
        timeout=25,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "1":
        return None
    return Decimal(str(data["result"])) / USDC_DECIMALS


async def _eth_balance(
    client: httpx.AsyncClient, address: str
) -> Decimal:
    try:
        balance_hex = await _rpc(client, "eth_getBalance", [address, "latest"])
        wei = int(balance_hex, 16)
        return Decimal(wei) / WEI
    except Exception as e:
        log.warning("eth_getBalance via RPC failed: %s", e)
        received = await _etherscan_balance_wei(client, address)
        if received is not None:
            log.info("eth balance via Etherscan fallback")
            return received
        raise


async def check_eth(
    client: httpx.AsyncClient, address: str, expected: Decimal
) -> MonitorResult:
    received = await _eth_balance(client, address)
    confirmed = received >= expected
    return MonitorResult(
        received=received,
        confirmed=confirmed,
        tx_ids=[],
        confirmations=1 if confirmed else 0,
    )


async def check_usdc_eth(
    client: httpx.AsyncClient, address: str, expected: Decimal
) -> MonitorResult:
    settings = get_settings()
    contract = settings.usdc_eth_contract
    data = "0x70a08231" + _pad_address(address)
    try:
        result = await _rpc(
            client,
            "eth_call",
            [{"to": contract, "data": data}, "latest"],
        )
        raw = int(result, 16)
        received = Decimal(raw) / USDC_DECIMALS
    except Exception as e:
        log.warning("usdc eth_call failed: %s", e)
        received = await _etherscan_usdc_balance(client, address)
        if received is None:
            raise
    confirmed = received >= expected
    return MonitorResult(
        received=received,
        confirmed=confirmed,
        tx_ids=[],
        confirmations=1 if confirmed else 0,
    )
