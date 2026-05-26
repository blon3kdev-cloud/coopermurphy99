"""Crypto BTC up/down bets — placement + listing.

Odds are computed server-side from current price, open price, remaining time
(log-normal with platform margin) so a slow client cannot lock in a stale price.
"""
from __future__ import annotations

import time
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from typing import Literal

from .. import btc_price
from ..crypto_fair_odds import calc_fair_crypto_odds
from ..db import get_db, next_id, now
from ..rate_limit import rate_limit_request
from ..rewards_service import record_vip_wager
from ..security import get_current_user

router = APIRouter(prefix="/api/crypto-bets", tags=["crypto-bets"])

_calc_odds = calc_fair_crypto_odds

_FEATURED_WINDOWS = ("5m", "30m", "24h")
_TITLE = {"5m": "5 min", "30m": "30 min", "24h": "24 h"}


def _fmt_price(p: float | None) -> str:
    if p is None:
        return "—"
    return f"{p:,.2f}".replace(",", "\u00a0") + "\u00a0$"


def _past_rounds(history: list[dict]) -> list[dict]:
    out: list[dict] = []
    for h in history[:5]:
        if h.get("direction") not in ("up", "down"):
            continue
        op = h.get("open_price")
        out.append({
            "direction": h["direction"],
            "openPrice": op,
            "priceToBeat": _fmt_price(op),
        })
    return out


def _build_featured() -> list[dict]:
    snap = btc_price.snapshot()
    price = snap["price"]
    out: list[dict] = []
    for win in _FEATURED_WINDOWS:
        w = snap["windows"][win]
        history = w.get("history") or []
        remaining = float(w["remainingSec"] or 0)
        odds = None
        if price is not None and w["openPrice"] is not None and remaining > 0:
            odds = calc_fair_crypto_odds(price, w["openPrice"], remaining, window=win)
        out.append({
            "id": f"k-btc-{win}",
            "title": f"Bitcoin: w górę czy w dół · {_TITLE[win]}",
            "name": "BTC/USD",
            "symbol": "btc",
            "color": "#f7931a",
            "window": win,
            "priceToBeat": _fmt_price(w["openPrice"]),
            "openPrice": w["openPrice"],
            "windowEnd": w.get("windowEnd"),
            "remainingSec": int(remaining),
            "odds": odds,
            "lastResolutions": w["resolutions"],
            "pastRounds": _past_rounds(history),
        })
    return out


@router.get("/featured")
async def list_featured() -> list[dict]:
    return _build_featured()


@router.get("")
async def list_all() -> list[dict]:
    return _build_featured()


class PlaceBody(BaseModel):
    window: Literal["5m", "30m", "24h"]
    direction: Literal["up", "down"]
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)


@router.post("/place")
async def place_bet(
    request: Request,
    payload: PlaceBody,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "crypto_bets.place", 30)
    snap = btc_price.snapshot()
    w = snap["windows"][payload.window]
    price = snap["price"]
    if price is None or w["openPrice"] is None or w["windowStart"] is None:
        raise HTTPException(status_code=503, detail="BTC data unavailable")

    now_ms = int(time.time() * 1000)
    end = w["windowEnd"]
    if end is None or end - now_ms < 10_000:
        raise HTTPException(status_code=400, detail="window closing soon")

    if user["balance_pln"] < payload.stakePln:
        raise HTTPException(status_code=400, detail="insufficient balance")

    remaining_sec = (end - now_ms) / 1000
    odds = _calc_odds(
        price,
        w["openPrice"],
        remaining_sec,
        window=payload.window,
    )[payload.direction]
    potential_win = (payload.stakePln * Decimal(str(odds))).quantize(Decimal("0.01"))

    db = get_db()
    updated = await db.users.find_one_and_update(
        {"id": user["id"], "balance_pln": {"$gte": payload.stakePln}},
        {"$inc": {"balance_pln": -payload.stakePln}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="insufficient balance")

    bet_id = await next_id("crypto_bets")
    await db.crypto_bets.insert_one(
        {
            "id": bet_id,
            "user_id": user["id"],
            "window": payload.window,
            "direction": payload.direction,
            "stake_pln": payload.stakePln,
            "odds": Decimal(str(odds)),
            "potential_win": potential_win,
            "open_price": Decimal(str(w["openPrice"])),
            "entry_price": Decimal(str(price)),
            "settle_price": None,
            "window_start": w["windowStart"],
            "settle_at": end,
            "status": "pending",
            "created_at": now(),
            "settled_at": None,
        }
    )
    await record_vip_wager(user["id"], payload.stakePln)
    return {
        "ok": True,
        "betId": bet_id,
        "odds": odds,
        "potentialWin": float(potential_win),
        "settleAt": end,
        "balance": float(updated["balance_pln"]),
    }
