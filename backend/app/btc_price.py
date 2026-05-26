"""Live BTC/USD price feed with clock-aligned 5 m / 30 m / 24 h windows.

Window boundaries use Europe/Warsaw (UTC+2 / CEST):
  5m  → :00, :05, :10, … each hour
  30m → :00, :30 each hour
  24h → 00:00 Warsaw

Persists per-window open price + last 5 closed rounds (direction + cena odniesienia).
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

import httpx
import websockets

from .config import get_settings
from .crypto_fair_odds import calc_fair_crypto_odds, fair_odds_service
from .db import get_db, now
from .rewards_service import record_vip_activity

log = logging.getLogger("btc")

POLL_INTERVAL = 10.0
FINAL_POLL_LEAD_SEC = 0.2
MIN_POLL_DELAY_SEC = 0.05
SHA256_EMPTY = hashlib.sha256(b"").hexdigest()
WARSAW = ZoneInfo("Europe/Warsaw")
MAX_HISTORY = 5

_PERIOD_MS = {"5m": 300_000, "30m": 1_800_000}


# ── window math (Europe/Warsaw) ──────────────────────────────────────────────

def _warsaw_midnight_ms(now_ms: int) -> int:
    dt = datetime.fromtimestamp(now_ms / 1000, tz=WARSAW)
    midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(midnight.timestamp() * 1000)


def _warsaw_period_start_ms(now_ms: int, period_ms: int) -> int:
    midnight_ms = _warsaw_midnight_ms(now_ms)
    elapsed = now_ms - midnight_ms
    return midnight_ms + (elapsed // period_ms) * period_ms


def window_start_ms(key: str, now_ms: int) -> int:
    if key in _PERIOD_MS:
        return _warsaw_period_start_ms(now_ms, _PERIOD_MS[key])
    return _warsaw_midnight_ms(now_ms)


def window_end_ms(key: str, start_ms: int) -> int:
    if key in _PERIOD_MS:
        return start_ms + _PERIOD_MS[key]
    return _warsaw_midnight_ms(start_ms + 25 * 3600_000)


def _next_poll_delay_sec(now_ms: int | None = None) -> float:
    """Binance poll interval; last poll in each 5m window lands before round end."""
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    start = window_start_ms("5m", now_ms)
    end = window_end_ms("5m", start)
    remaining = max(0.0, (end - now_ms) / 1000)
    if remaining <= 0:
        return POLL_INTERVAL
    slots = int((remaining - FINAL_POLL_LEAD_SEC) // POLL_INTERVAL)
    if slots <= 0:
        return max(MIN_POLL_DELAY_SEC, remaining - FINAL_POLL_LEAD_SEC)
    return POLL_INTERVAL


# ── shared state ─────────────────────────────────────────────────────────────

def _empty_window() -> dict[str, Any]:
    return {"open_price": None, "window_start": None, "history": []}


_state: dict[str, Any] = {
    "price": None,
    "last_fetched": 0,
    "windows": {k: _empty_window() for k in ("5m", "30m", "24h")},
}

_subscribers: set[asyncio.Queue[str]] = set()


def _history_directions(history: list[dict]) -> list[str]:
    return [h["direction"] for h in history if h.get("direction") in ("up", "down")]


def _trim_history(history: list[dict]) -> list[dict]:
    return history[:MAX_HISTORY]


def _prepend_history(
    w: dict[str, Any],
    direction: str,
    open_price: float,
    settle_price: float,
    window_start: int,
) -> None:
    entry = {
        "direction": direction,
        "open_price": open_price,
        "settle_price": settle_price,
        "window_start": window_start,
    }
    w["history"] = _trim_history([entry] + list(w.get("history") or []))


def _any_window_expired(now_ms: int) -> bool:
    for key, w in _state["windows"].items():
        if w["window_start"] is None:
            continue
        if window_end_ms(key, w["window_start"]) <= now_ms:
            return True
    return False


async def _advance_expired_windows() -> bool:
    """Close ended rounds and push SSE — used when the clock passes window end."""
    price = _state["price"]
    if price is None or not _any_window_expired(int(time.time() * 1000)):
        return False
    closed, dirty = _tick_windows(price)
    for key, ws, settle, opn in closed:
        dirty.add(key)
        asyncio.create_task(_settle_window(key, ws, settle, opn))
    for key in dirty:
        asyncio.create_task(_persist_window(key))
    await _publish_snapshot()
    return True


def snapshot() -> dict:
    now_ms = int(time.time() * 1000)
    price = _state["price"]
    wins = {}
    for k, w in _state["windows"].items():
        end = window_end_ms(k, w["window_start"]) if w["window_start"] else None
        remaining = max(0.0, (end - now_ms) / 1000) if end is not None else None
        history = list(w.get("history") or [])
        odds = None
        if (
            price is not None
            and w["open_price"] is not None
            and remaining is not None
            and remaining > 0
        ):
            odds = calc_fair_crypto_odds(
                price,
                w["open_price"],
                remaining,
                window=k,
            )
            odds_ctx = fair_odds_service.odds_context(remaining, window=k)
        else:
            odds_ctx = None
        wins[k] = {
            "openPrice": w["open_price"],
            "windowStart": w["window_start"],
            "windowEnd": end,
            "remainingSec": remaining,
            "history": history,
            "resolutions": _history_directions(history),
            "odds": odds,
            "oddsContext": odds_ctx,
        }
    out = {"price": price, "windows": wins, "ts": _state["last_fetched"]}
    out.update(fair_odds_service.snapshot_extras())
    return out


def subscribe() -> asyncio.Queue[str]:
    q: asyncio.Queue[str] = asyncio.Queue(maxsize=8)
    _subscribers.add(q)
    return q


def unsubscribe(q: asyncio.Queue[str]) -> None:
    _subscribers.discard(q)


async def _publish_snapshot() -> None:
    payload = json.dumps(snapshot())
    for q in list(_subscribers):
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            unsubscribe(q)


# ── persistence ──────────────────────────────────────────────────────────────

def _normalize_history(raw: Any) -> list[dict]:
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, str) and item in ("up", "down"):
            out.append({"direction": item, "open_price": None, "settle_price": None, "window_start": None})
            continue
        if not isinstance(item, dict):
            continue
        d = item.get("direction")
        if d not in ("up", "down"):
            continue
        op = item.get("open_price")
        sp = item.get("settle_price")
        ws = item.get("window_start")
        out.append({
            "direction": d,
            "open_price": float(op) if op is not None else None,
            "settle_price": float(sp) if sp is not None else None,
            "window_start": int(ws) if ws is not None else None,
        })
    return _trim_history(out)


async def _load_windows_from_db() -> None:
    try:
        cursor = get_db().krypto_market_resolutions.find()
        async for r in cursor:
            key = r.get("window")
            w = _state["windows"].get(key)
            if not w:
                continue
            legacy = r.get("resolutions") or []
            history = _normalize_history(r.get("history") or legacy)
            w["history"] = history
            ws = r.get("window_start")
            op = r.get("open_price")
            if ws is not None:
                w["window_start"] = int(ws)
            if op is not None:
                w["open_price"] = float(op)
    except Exception as exc:
        log.warning("load krypto windows: %s", exc)


async def _persist_window(win: str) -> None:
    w = _state["windows"][win]
    try:
        await get_db().krypto_market_resolutions.update_one(
            {"window": win},
            {
                "$set": {
                    "window_start": w["window_start"],
                    "open_price": w["open_price"],
                    "history": w.get("history") or [],
                    "updated_at": now(),
                }
            },
            upsert=True,
        )
    except Exception as exc:
        log.warning("persist window %s failed: %s", win, exc)


async def _settle_window(win: str, window_start: int, settle_price: float, open_price: float) -> None:
    outcome = "up" if settle_price >= open_price else "down"
    try:
        db = get_db()
        cursor = db.crypto_bets.find(
            {"window": win, "window_start": window_start, "status": "pending"}
        )
        from .parlay_settlement import try_finalize_parlay

        async for b in cursor:
            won = b["direction"] == outcome
            gid = b.get("slip_group_id")
            await db.crypto_bets.update_one(
                {"id": b["id"]},
                {
                    "$set": {
                        "status": "won" if won else "lost",
                        "settled_at": now(),
                        "settle_price": Decimal(str(settle_price)),
                    }
                },
            )
            if gid is not None:
                await try_finalize_parlay(gid, b["user_id"])
                continue
            if won:
                stake = b.get("slip_stake_pln") or b["stake_pln"]
                payout = b.get("potential_win") or (stake * b["odds"])
                await db.users.update_one(
                    {"id": b["user_id"]},
                    {"$inc": {"balance_pln": payout}},
                )
                await record_vip_activity(b["user_id"], Decimal(0), Decimal(str(payout)))
    except Exception as exc:
        log.warning("crypto-bet settlement error: %s", exc)


def _next_window_start(key: str, start_ms: int) -> int:
    if key in _PERIOD_MS:
        return start_ms + _PERIOD_MS[key]
    return window_end_ms(key, start_ms)


def _close_window(
    key: str,
    w: dict[str, Any],
    settle_price: float,
) -> tuple[int, float, float] | None:
    if w["window_start"] is None or w["open_price"] is None:
        return None
    old_start = w["window_start"]
    open_price = w["open_price"]
    direction = "up" if settle_price >= open_price else "down"
    _prepend_history(w, direction, open_price, settle_price, old_start)
    return old_start, settle_price, open_price


def _tick_windows(price: float) -> tuple[list[tuple[str, int, float, float]], set[str]]:
    """Advance windows to Warsaw clock; close missed periods after downtime."""
    now_ms = int(time.time() * 1000)
    closed: list[tuple[str, int, float, float]] = []
    dirty: set[str] = set()
    for key, w in _state["windows"].items():
        current_start = window_start_ms(key, now_ms)
        if w["window_start"] is None:
            w["window_start"] = current_start
            w["open_price"] = price
            dirty.add(key)
            continue
        if w["window_start"] > current_start:
            w["window_start"] = current_start
            w["open_price"] = price
            dirty.add(key)
            continue
        while w["window_start"] < current_start:
            info = _close_window(key, w, price)
            if info:
                closed.append((key, *info))
            w["window_start"] = _next_window_start(key, w["window_start"])
            w["open_price"] = price
            dirty.add(key)
    return closed, dirty


async def _publish_price(price: float) -> None:
    price = round(float(price), 2)
    ts_ms = int(time.time() * 1000)
    _state["price"] = price
    _state["last_fetched"] = ts_ms
    fair_odds_service.record_price(price, ts_ms)
    closed, dirty = _tick_windows(price)
    for key, ws, settle, opn in closed:
        dirty.add(key)
        asyncio.create_task(_settle_window(key, ws, settle, opn))
    for key in dirty:
        asyncio.create_task(_persist_window(key))
    await _publish_snapshot()


# ── Binance REST poll (fallback) ─────────────────────────────────────────────

async def _binance_poll_loop() -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            try:
                r = await client.get(
                    "https://api.binance.com/api/v3/ticker/price",
                    params={"symbol": "BTCUSDT"},
                )
                r.raise_for_status()
                price = float(r.json()["price"])
                if price > 0:
                    await _publish_price(price)
            except Exception as exc:
                log.warning("binance poll error: %s", exc)
            await asyncio.sleep(_next_poll_delay_sec())


# ── Chainlink Data Streams v3 (primary) ──────────────────────────────────────

def _chainlink_headers(full_path: str) -> dict[str, str]:
    s = get_settings()
    ts = str(int(time.time() * 1000))
    string_to_sign = f"GET {full_path} {SHA256_EMPTY} {s.chainlink_api_key} {ts}"
    sig = hmac.new(s.chainlink_api_secret.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()
    return {
        "Authorization": s.chainlink_api_key,
        "X-Authorization-Timestamp": ts,
        "X-Authorization-Signature-SHA256": sig,
    }


def _decode_v3_benchmark_price(full_report_hex: str) -> float | None:
    buf = bytes.fromhex(full_report_hex.removeprefix("0x"))
    HEAD = 96
    if len(buf) < HEAD + 32:
        return None
    blob_offset = int.from_bytes(buf[HEAD:HEAD + 32], "big")
    blob_start = HEAD + blob_offset
    if len(buf) < blob_start + 32:
        return None
    blob_len = int.from_bytes(buf[blob_start:blob_start + 32], "big")
    blob = buf[blob_start + 32:blob_start + 32 + blob_len]
    if len(blob) < 7 * 32:
        return None
    slot = blob[6 * 32:7 * 32]
    p = int.from_bytes(slot, "big")
    if p >= 2 ** 191:
        p -= 2 ** 192
    return p / 1e18


async def _chainlink_ws_loop() -> None:
    s = get_settings()
    feed_path = f"/api/v1/ws?feedIDs={quote(s.chainlink_feed_id, safe='')}"
    url = f"{s.chainlink_ws_url}{feed_path}"
    while True:
        try:
            async with websockets.connect(
                url,
                additional_headers=_chainlink_headers(feed_path),
                ping_interval=5,
                ping_timeout=10,
                max_size=None,
            ) as ws:
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                        full = msg.get("report", {}).get("fullReport")
                        if not full:
                            continue
                        price = _decode_v3_benchmark_price(full)
                        if price and price > 0:
                            await _publish_price(price)
                    except Exception as exc:
                        log.warning("chainlink parse: %s", exc)
        except Exception as exc:
            log.warning("chainlink ws: %s", exc)
        await asyncio.sleep(5)


# ── boot ────────────────────────────────────────────────────────────────────

_task: asyncio.Task | None = None
_clock_task: asyncio.Task | None = None


async def _clock_sync_loop() -> None:
    """Publish fresh window boundaries as soon as a round ends."""
    while True:
        await asyncio.sleep(1.0)
        try:
            await _advance_expired_windows()
        except Exception as exc:
            log.warning("clock sync: %s", exc)


async def start() -> None:
    global _task, _clock_task
    if _task is not None:
        return
    await _load_windows_from_db()
    feed = _chainlink_ws_loop if get_settings().use_chainlink else _binance_poll_loop
    _task = asyncio.create_task(feed(), name="btc-price-feed")
    _clock_task = asyncio.create_task(_clock_sync_loop(), name="btc-window-clock")


async def stop() -> None:
    global _task, _clock_task
    if _clock_task is not None:
        _clock_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _clock_task
        _clock_task = None
    if _task is None:
        return
    _task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _task
    _task = None
