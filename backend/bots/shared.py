"""Shared helpers for Discord and Telegram bots."""
from __future__ import annotations

import logging
import os
import secrets
from datetime import date
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

log = logging.getLogger("bots.shared")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:4000").rstrip("/")
INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", "").strip()
CZUTKA_NICK_TAG = "czutkabet.com"
WARSAW = ZoneInfo("Europe/Warsaw")


class BackendError(Exception):
    def __init__(self, status: int, data: dict) -> None:
        super().__init__(data.get("error") or data.get("detail") or "backend error")
        self.status = status
        self.data = data if isinstance(data, dict) else {}


async def call_backend(path: str, body: dict | None = None, *, method: str = "POST") -> dict:
    url = f"{BACKEND_URL}{path}"
    headers = {"x-internal-secret": INTERNAL_SECRET, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        if method.upper() == "GET":
            r = await client.get(url, headers=headers)
        else:
            r = await client.post(url, json=body or {}, headers=headers)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if not r.is_success:
            raise BackendError(r.status_code, data)
        return data


def dummy_daily_code(d: date | None = None) -> str:
    del d
    return f"DAILY_{secrets.token_hex(8).upper()}"


def dummy_reward_code() -> str:
    return f"DISCORD_{secrets.token_hex(8).upper()}"


def withdraw_balance_error(amount_pln: Decimal, balance_pln: Decimal) -> str | None:
    """Return a user-facing error if amount exceeds balance, else None."""
    if amount_pln <= balance_pln:
        return None
    return (
        "❌ **Insufficient balance**\n\n"
        f"**Available:** {balance_pln:.2f} PLN\n"
        f"**Requested:** {amount_pln:.2f} PLN\n\n"
        "Lower the withdrawal amount or deposit more funds first."
    )


def format_insufficient_balance_detail(detail: object) -> str | None:
    if detail == "insufficient balance":
        return (
            "❌ **Insufficient balance** — you cannot withdraw more than your current PLN balance."
        )
    return None


def format_playthrough_withdraw_detail(detail: object) -> str | None:
    if not isinstance(detail, dict) or detail.get("code") != "withdraw_playthrough_required":
        return None
    remaining = Decimal(str(detail.get("remainingWagerPln", 0)))
    required = Decimal(str(detail.get("requiredTotalWagerPln", 0)))
    wagered = Decimal(str(detail.get("wageredPln", 0)))
    multiplier = int(detail.get("multiplier") or 5)
    return (
        "❌ **Withdrawal blocked — playthrough required**\n\n"
        f"Deposits and other balance credits must be wagered at least **{multiplier}×** "
        "before you can withdraw.\n\n"
        f"**Wagered so far:** {wagered:.2f} PLN\n"
        f"**Required total:** {required:.2f} PLN\n"
        f"**Still needed:** **{remaining:.2f} PLN** in bets\n\n"
        "Place bets on the site to unlock withdrawals."
    )


def format_withdraw_detail(detail: object) -> str | None:
    msg = format_playthrough_withdraw_detail(detail)
    if msg:
        return msg
    return format_insufficient_balance_detail(detail)


def format_cooldown(ms_left: int) -> str:
    """Human-readable time left."""
    total_sec = max(0, ms_left // 1000)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    if hours > 0:
        return f"{hours} hr {minutes} min"
    if minutes > 0:
        return f"{minutes} min"
    return f"{total_sec} sec"


def has_czutka_tag(*names: str | None) -> bool:
    return any(CZUTKA_NICK_TAG in (n or "").lower() for n in names)


def channel_id(name: str, *legacy_names: str) -> str:
    """Read channel ID from env with optional legacy fallbacks."""
    val = os.environ.get(name, "").strip()
    if val:
        return val
    for legacy in legacy_names:
        val = os.environ.get(legacy, "").strip()
        if val:
            return val
    return ""


async def _binance_usd_price(symbol: str) -> Decimal:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": symbol},
        )
        r.raise_for_status()
        return Decimal(r.json()["price"])


async def pln_to_crypto(asset: str, pln: Decimal) -> Decimal:
    """Convert PLN to crypto amount using USD/PLN rate and live USD prices."""
    usd_pln = Decimal(os.environ.get("USD_PLN_RATE", "4.0"))
    if usd_pln <= 0:
        raise ValueError("Invalid USD_PLN_RATE configuration")
    usd = pln / usd_pln
    asset_l = asset.lower()
    if asset_l in ("usdc_eth", "usdc_sol"):
        amount = usd
        decimals = 6
    elif asset_l == "btc":
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{BACKEND_URL}/api/bitcoin")
            r.raise_for_status()
            btc_usd = Decimal(str(r.json()["price"]))
        if btc_usd <= 0:
            raise ValueError("BTC price unavailable")
        amount = usd / btc_usd
        decimals = 8
    elif asset_l == "eth":
        eth_usd = await _binance_usd_price("ETHUSDT")
        amount = usd / eth_usd
        decimals = 8
    elif asset_l == "sol":
        sol_usd = await _binance_usd_price("SOLUSDT")
        amount = usd / sol_usd
        decimals = 9
    else:
        raise ValueError("Unsupported asset")
    q = Decimal(10) ** -decimals
    return amount.quantize(q, rounding=ROUND_DOWN)


def schedule_daily_discord_post(send_fn) -> AsyncIOScheduler:
    """Schedule midnight Warsaw daily code post. send_fn is async callable with no args."""
    scheduler = AsyncIOScheduler(timezone=WARSAW)

    async def _job() -> None:
        try:
            await send_fn()
        except Exception:
            log.exception("daily code post failed")

    scheduler.add_job(
        _job,
        CronTrigger(hour=0, minute=0, timezone=WARSAW),
        id="daily_code",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
