"""Per-user bet history — active / history / place slip (markets + crypto parlay)."""
from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from typing import Literal, Optional

from .. import btc_price
from ..db import as_utc, get_db, next_id, now
from ..market_utils import (
    format_bet_day,
    format_event_date,
    is_open_for_betting,
    market_bet_start_at,
    parse_iso_date,
)
from ..crypto_fair_odds import calc_fair_crypto_odds as _calc_odds
from ..crypto_odds import CRYPTO_MIN_ODDS
from ..rate_limit import rate_limit_request
from ..rewards_service import record_vip_wager
from ..security import get_current_user

router = APIRouter(prefix="/api/user/bets", tags=["user-bets"])

_CRYPTO_TITLE = {"5m": "5 min", "30m": "30 min", "24h": "24 h"}


def _fmt(amount) -> str:
    return f"{float(amount):,.2f}".replace(",", "\u00a0").replace(".", ",")


def _crypto_title(window: str) -> str:
    return f"Bitcoin: w górę czy w dół · {_CRYPTO_TITLE.get(window, window)}"


def _crypto_answer(direction: str) -> str:
    return "Wyżej" if direction == "up" else "Niżej"


def _fmt_bet_date(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    text = format_event_date(as_utc(dt))
    return text or None


def _crypto_settle_date(settle_at) -> str | None:
    if settle_at is None:
        return None
    try:
        ms = int(settle_at)
    except (TypeError, ValueError):
        return None
    return _fmt_bet_date(datetime.fromtimestamp(ms / 1000, tz=timezone.utc))


async def _markets_by_id(db, market_ids: list) -> dict[str, dict]:
    unique = list(dict.fromkeys(str(mid) for mid in market_ids if mid is not None))
    if not unique:
        return {}
    cursor = db.markets.find({"id": {"$in": unique}})
    return {str(r["id"]): r async for r in cursor}


def _market_event_date(market: dict) -> str | None:
    dt = market_bet_start_at(market)
    if dt is not None:
        return _fmt_bet_date(dt)
    return _fmt_bet_date(market.get("created_at"))


def _active_row(
    *,
    bet_id: int,
    kind: str,
    title: str,
    answer: str,
    multiplier: str,
    cost: str,
    pot_win: str,
    image: str | None = None,
    symbol: str | None = None,
    slip_group_id: int | None = None,
    event_date: str | None = None,
) -> dict:
    row = {
        "id": bet_id,
        "kind": kind,
        "title": title,
        "answer": answer,
        "multiplier": multiplier,
        "cost": cost,
        "potWin": pot_win,
    }
    if image:
        row["image"] = image
    if symbol:
        row["symbol"] = symbol
    if slip_group_id is not None:
        row["slipGroupId"] = slip_group_id
    if event_date:
        row["eventDate"] = event_date
    return row


async def _parlay_potential(db, user_id: int, slip_group_id: int, stake: Decimal) -> Decimal:
    combined = Decimal("1")
    for coll in ("market_bets", "crypto_bets"):
        cursor = db[coll].find(
            {"user_id": user_id, "slip_group_id": slip_group_id, "status": "pending"},
        )
        async for leg in cursor:
            combined *= leg["odds"]
    return (stake * combined).quantize(Decimal("0.01"))


@router.get("/active")
async def get_active(user: dict = Depends(get_current_user)) -> list[dict]:
    db = get_db()
    raw: list[dict] = []

    pending_market_rows: list[dict] = []
    cursor = db.market_bets.find({"user_id": user["id"], "status": "pending"}).sort("created_at", -1)
    async for r in cursor:
        pending_market_rows.append(r)

    markets_map = await _markets_by_id(db, [r["market_id"] for r in pending_market_rows])
    for r in pending_market_rows:
        m = markets_map.get(str(r["market_id"]))
        if not m:
            continue
        yes_l = m.get("yes_label", "Yes")
        no_l = m.get("no_label", "No")
        raw.append(
            {
                "created_at": r["created_at"],
                "id": r["id"],
                "kind": "market",
                "title": m["title"],
                "answer": yes_l if r["side"] == "yes" else no_l,
                "multiplier": f"{float(r['odds']):.2f}x",
                "image": m.get("image"),
                "event_date": _market_event_date(m),
                "slip_group_id": r.get("slip_group_id"),
                "slip_stake_pln": r.get("slip_stake_pln"),
                "stake_pln": r["stake_pln"],
                "odds": r["odds"],
            }
        )

    cursor = db.crypto_bets.find({"user_id": user["id"], "status": "pending"}).sort("created_at", -1)
    async for r in cursor:
        raw.append(
            {
                "created_at": r["created_at"],
                "id": r["id"],
                "kind": "crypto",
                "title": _crypto_title(r["window"]),
                "answer": _crypto_answer(r["direction"]),
                "multiplier": f"{float(r['odds']):.2f}x",
                "symbol": "btc",
                "event_date": _crypto_settle_date(r.get("settle_at")),
                "slip_group_id": r.get("slip_group_id"),
                "slip_stake_pln": r.get("slip_stake_pln"),
                "stake_pln": r["stake_pln"],
                "odds": r["odds"],
            }
        )

    raw.sort(key=lambda x: x["created_at"], reverse=True)

    pot_cache: dict[int, Decimal] = {}
    out: list[dict] = []
    for r in raw:
        gid = r.get("slip_group_id")
        stake = r.get("slip_stake_pln") or r["stake_pln"]
        if gid is not None:
            if gid not in pot_cache:
                pot_cache[gid] = await _parlay_potential(db, user["id"], gid, stake)
            pot = pot_cache[gid]
            cost = _fmt(stake)
        else:
            pot = (stake * r["odds"]).quantize(Decimal("0.01"))
            cost = _fmt(stake)

        out.append(
            _active_row(
                bet_id=r["id"],
                kind=r["kind"],
                title=r["title"],
                answer=r["answer"],
                multiplier=r["multiplier"],
                cost=cost,
                pot_win=_fmt(pot),
                image=r.get("image"),
                symbol=r.get("symbol"),
                slip_group_id=gid,
                event_date=r.get("event_date"),
            )
        )
    return out


def _parse_before_cursor(before: str | None) -> datetime | None:
    if not before:
        return None
    raw = before.strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid before cursor") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _history_groups_from_rows(rows: list[dict]) -> list[dict]:
    clusters: dict[tuple[str, str], list] = defaultdict(list)
    for r in rows:
        day = format_bet_day(r["created_at"])
        gid = r.get("slip_group_id")
        key = (day, f"g{gid}") if gid is not None else (day, f"s{r['id']}")
        clusters[key].append(r)

    out = []
    for (day, _), items in clusters.items():
        items.sort(key=lambda x: x["created_at"], reverse=True)
        stake = items[0].get("slip_stake_pln") or items[0]["stake_pln"]
        is_parlay = items[0].get("slip_group_id") is not None and len(items) > 1
        if is_parlay:
            total_cost = stake
        else:
            total_cost = sum((i.get("slip_stake_pln") or i["stake_pln"] for i in items), Decimal(0))

        total_win = Decimal(0)
        if is_parlay and items[0].get("slip_paid"):
            total_win = items[0].get("slip_potential_win") or Decimal(0)
        else:
            for leg in items:
                stake_leg = leg.get("slip_stake_pln") or leg["stake_pln"]
                if leg["status"] == "won":
                    if leg["kind"] == "crypto":
                        total_win += leg.get("potential_win") or (stake_leg * leg["odds"])
                    else:
                        total_win += stake_leg * leg["odds"]
                elif leg["status"] == "cashback":
                    total_win += stake_leg

        out.append(
            {
                "date": day,
                "ended": True,
                "isParlay": is_parlay,
                "sortAt": items[0]["created_at"],
                "bets": [
                    {
                        "id": leg["id"],
                        "kind": leg["kind"],
                        "title": leg["title"],
                        "answer": leg.get("answer_label", "Yes" if leg.get("side") == "yes" else "No"),
                        "multiplier": f"{float(leg['odds']):.2f}x",
                        "image": leg.get("image"),
                        "symbol": leg.get("symbol"),
                        "eventDate": leg.get("event_date"),
                        "ended": True,
                    }
                    for leg in items
                ],
                "totalCost": _fmt(total_cost),
                "totalWin": _fmt(total_win),
            }
        )

    out.sort(key=lambda g: g["sortAt"], reverse=True)
    return out


async def _fetch_history_rows(db, user_id: int, *, before_dt: datetime | None, raw_limit: int) -> list[dict]:
    base_q: dict = {"user_id": user_id, "status": {"$ne": "pending"}}
    if before_dt is not None:
        base_q["created_at"] = {"$lt": before_dt}

    history_market_rows: list[dict] = []
    cursor = db.market_bets.find(base_q).sort("created_at", -1).limit(raw_limit)
    async for r in cursor:
        history_market_rows.append(r)

    markets_map = await _markets_by_id(db, [r["market_id"] for r in history_market_rows])
    rows: list[dict] = []
    for r in history_market_rows:
        m = markets_map.get(str(r["market_id"]))
        if not m:
            continue
        yes_l = m.get("yes_label", "Yes")
        no_l = m.get("no_label", "No")
        rows.append(
            {
                **r,
                "kind": "market",
                "title": m["title"],
                "image": m.get("image"),
                "answer_label": yes_l if r["side"] == "yes" else no_l,
                "event_date": _market_event_date(m),
            }
        )

    cursor = db.crypto_bets.find(base_q).sort("created_at", -1).limit(raw_limit)
    async for r in cursor:
        settled = r.get("settled_at")
        event_date = _fmt_bet_date(settled) if settled else _crypto_settle_date(r.get("settle_at"))
        rows.append(
            {
                **r,
                "kind": "crypto",
                "title": _crypto_title(r["window"]),
                "symbol": "btc",
                "answer_label": _crypto_answer(r["direction"]),
                "event_date": event_date,
            }
        )

    rows.sort(key=lambda x: x["created_at"], reverse=True)
    return rows


@router.get("/history")
async def get_history(
    user: dict = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=50),
    before: Optional[str] = Query(default=None),
) -> dict:
    db = get_db()
    before_dt = _parse_before_cursor(before)
    rows = await _fetch_history_rows(db, user["id"], before_dt=before_dt, raw_limit=120)
    groups = _history_groups_from_rows(rows)
    page = groups[:limit]

    next_before = None
    if len(page) == limit and page:
        oldest = page[-1]["sortAt"]
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        next_before = oldest.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    for g in page:
        g.pop("sortAt", None)

    return {"items": page, "nextBefore": next_before}


def _leg_settled_at(leg: dict):
    return leg.get("settled_at") or leg.get("created_at")


def _group_fully_won(legs: list[dict]) -> bool:
    if not legs:
        return False
    statuses = [b["status"] for b in legs]
    if any(s == "pending" for s in statuses):
        return False
    if any(s == "lost" for s in statuses):
        return False
    return all(s in ("won", "cashback") for s in statuses)


def _group_total_win(legs: list[dict]) -> Decimal:
    gid = legs[0].get("slip_group_id")
    is_parlay = gid is not None and len(legs) > 1
    stake = legs[0].get("slip_stake_pln") or legs[0]["stake_pln"]
    if is_parlay:
        slip_win = legs[0].get("slip_potential_win")
        if slip_win is not None:
            return Decimal(str(slip_win))
        combined = Decimal("1")
        for b in legs:
            combined *= b["odds"]
        return (stake * combined).quantize(Decimal("0.01"))
    leg = legs[0]
    stake_leg = leg.get("slip_stake_pln") or leg["stake_pln"]
    if leg["status"] == "won":
        if leg.get("kind") == "crypto" or "window" in leg:
            return leg.get("potential_win") or (stake_leg * leg["odds"])
        return stake_leg * leg["odds"]
    return stake_leg


async def _enrich_market_leg(db, r: dict) -> dict | None:
    m = await db.markets.find_one({"id": r["market_id"]})
    if not m:
        return None
    yes_l = m.get("yes_label", "Yes")
    no_l = m.get("no_label", "No")
    return {
        **r,
        "kind": "market",
        "title": m["title"],
        "image": m.get("image"),
        "answer_label": yes_l if r["side"] == "yes" else no_l,
        "event_date": _market_event_date(m),
    }


def _enrich_crypto_leg(r: dict) -> dict:
    settled = r.get("settled_at")
    event_date = _fmt_bet_date(settled) if settled else _crypto_settle_date(r.get("settle_at"))
    return {
        **r,
        "kind": "crypto",
        "title": _crypto_title(r["window"]),
        "symbol": "btc",
        "answer_label": _crypto_answer(r["direction"]),
        "event_date": event_date,
    }


def _celebration_bet_rows(legs: list[dict], total_cost: Decimal, total_win: Decimal) -> list[dict]:
    is_parlay = legs[0].get("slip_group_id") is not None and len(legs) > 1
    cost_fmt = _fmt(total_cost)
    win_fmt = _fmt(total_win)
    rows = []
    for i, r in enumerate(sorted(legs, key=lambda x: x.get("created_at") or 0)):
        row = {
            "id": r["id"],
            "kind": r["kind"],
            "title": r["title"],
            "answer": r.get("answer_label", "Yes" if r.get("side") == "yes" else "No"),
            "multiplier": f"{float(r['odds']):.2f}x",
            "image": r.get("image"),
            "symbol": r.get("symbol"),
            "eventDate": r.get("event_date"),
        }
        if not is_parlay or i == len(legs) - 1:
            row["cost"] = cost_fmt
            row["potWin"] = win_fmt
        rows.append(row)
    return rows


async def _pending_win_celebration(db, user_id: int) -> dict | None:
    candidates: list[tuple[datetime, str, list[dict]]] = []

    slip_ids: set[int] = set()
    for coll in ("market_bets", "crypto_bets"):
        cursor = db[coll].find(
            {
                "user_id": user_id,
                "slip_group_id": {"$ne": None},
                "celebration_shown": {"$ne": True},
            },
            {"slip_group_id": 1},
        )
        async for r in cursor:
            gid = r.get("slip_group_id")
            if gid is not None:
                slip_ids.add(int(gid))

    for gid in slip_ids:
        legs: list[dict] = []
        for coll in ("market_bets", "crypto_bets"):
            cursor = db[coll].find({"user_id": user_id, "slip_group_id": gid})
            async for r in cursor:
                if coll == "market_bets":
                    enriched = await _enrich_market_leg(db, r)
                    if enriched:
                        legs.append(enriched)
                else:
                    legs.append(_enrich_crypto_leg(r))
        if len(legs) < 2 or not _group_fully_won(legs):
            continue
        if any(b.get("celebration_shown") for b in legs):
            continue
        settled = max(_leg_settled_at(b) for b in legs)
        candidates.append((settled, f"slip:{gid}", legs))

    for coll, kind in (("market_bets", "market"), ("crypto_bets", "crypto")):
        cursor = db[coll].find(
            {
                "user_id": user_id,
                "status": "won",
                "slip_group_id": None,
                "celebration_shown": {"$ne": True},
            },
        )
        async for r in cursor:
            if coll == "market_bets":
                leg = await _enrich_market_leg(db, r)
            else:
                leg = _enrich_crypto_leg(r)
            if leg is None:
                continue
            settled = _leg_settled_at(leg)
            candidates.append((settled, f"{kind}:{r['id']}", [leg]))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    _, key, legs = candidates[0]
    stake = legs[0].get("slip_stake_pln") or legs[0]["stake_pln"]
    is_parlay = legs[0].get("slip_group_id") is not None and len(legs) > 1
    if is_parlay:
        total_cost = stake
    else:
        total_cost = stake
    total_win = _group_total_win(legs)
    return {
        "celebrationKey": key,
        "isParlay": is_parlay,
        "totalWin": _fmt(total_win),
        "bets": _celebration_bet_rows(legs, total_cost, total_win),
    }


@router.get("/celebration")
async def get_pending_celebration(user: dict = Depends(get_current_user)) -> Optional[dict]:
    db = get_db()
    return await _pending_win_celebration(db, user["id"])


class DismissCelebrationBody(BaseModel):
    celebrationKey: str = Field(min_length=3, max_length=64)


@router.post("/celebration/dismiss")
async def dismiss_celebration(
    payload: DismissCelebrationBody,
    user: dict = Depends(get_current_user),
) -> dict:
    db = get_db()
    key = payload.celebrationKey.strip()
    if key.startswith("slip:"):
        try:
            gid = int(key.split(":", 1)[1])
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid celebration key") from exc
        for coll in ("market_bets", "crypto_bets"):
            await db[coll].update_many(
                {"user_id": user["id"], "slip_group_id": gid},
                {"$set": {"celebration_shown": True}},
            )
        return {"ok": True}

    if key.startswith("market:") or key.startswith("crypto:"):
        kind, _, raw_id = key.partition(":")
        try:
            bet_id = int(raw_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid celebration key") from exc
        coll = "market_bets" if kind == "market" else "crypto_bets"
        await db[coll].update_one(
            {"user_id": user["id"], "id": bet_id},
            {"$set": {"celebration_shown": True}},
        )
        return {"ok": True}

    raise HTTPException(status_code=400, detail="invalid celebration key")


class SlipItem(BaseModel):
    marketId: str
    side: Literal["yes", "no"]
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)


class Slip(BaseModel):
    items: list[SlipItem] = Field(min_length=1, max_length=20)


class CryptoSlipItem(BaseModel):
    window: Literal["5m", "30m", "24h"]
    direction: Literal["up", "down"]


class ParlayMarketItem(BaseModel):
    marketId: str
    side: Literal["yes", "no"]


class Parlay(BaseModel):
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    markets: list[ParlayMarketItem] = Field(default_factory=list, max_length=20)
    crypto: list[CryptoSlipItem] = Field(default_factory=list, max_length=10)


@router.post("/parlay")
async def place_parlay(
    request: Request,
    payload: Parlay,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "user_bets.parlay", 30)
    if not payload.markets and not payload.crypto:
        raise HTTPException(status_code=400, detail="empty slip")

    db = get_db()
    stake = payload.stakePln
    leg_count = len(payload.markets) + len(payload.crypto)
    is_parlay = leg_count > 1

    markets_map = await _markets_by_id(db, [item.marketId for item in payload.markets])
    market_plan: list[tuple[ParlayMarketItem, Decimal]] = []
    for item in payload.markets:
        market = markets_map.get(str(item.marketId))
        if market is None or not is_open_for_betting(market):
            raise HTTPException(status_code=400, detail="market not available")
        odds = market["yes_odds"] if item.side == "yes" else market["no_odds"]
        market_plan.append((item, odds))

    crypto_plan: list[tuple[CryptoSlipItem, Decimal, dict, float, int]] = []
    snap = btc_price.snapshot() if payload.crypto else None
    now_ms = int(time.time() * 1000)

    for item in payload.crypto:
        if snap is None:
            raise HTTPException(status_code=503, detail="BTC data unavailable")
        w = snap["windows"][item.window]
        price = snap["price"]
        if price is None or w["openPrice"] is None or w["windowStart"] is None:
            raise HTTPException(status_code=503, detail="BTC data unavailable")
        end = w["windowEnd"]
        if end is None or end - now_ms < 10_000:
            raise HTTPException(status_code=400, detail="window closing soon")
        remaining_sec = (end - now_ms) / 1000
        odds_f = _calc_odds(
            price,
            w["openPrice"],
            remaining_sec,
            window=item.window,
        )[item.direction]
        if odds_f < CRYPTO_MIN_ODDS:
            raise HTTPException(status_code=400, detail="crypto odds too low")
        crypto_plan.append((item, Decimal(str(odds_f)), w, price, end))

    combined = Decimal("1")
    for _, odds in market_plan:
        combined *= odds
    for _, odds, _, _, _ in crypto_plan:
        combined *= odds
    slip_potential = (stake * combined).quantize(Decimal("0.01"))

    if user["balance_pln"] < stake:
        raise HTTPException(status_code=400, detail="insufficient balance")

    updated = await db.users.find_one_and_update(
        {"id": user["id"], "balance_pln": {"$gte": stake}},
        {"$inc": {"balance_pln": -stake}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="insufficient balance")

    slip_group_id = await next_id("bet_slip_groups") if is_parlay else None
    placed_market: list[int] = []
    placed_crypto: list[int] = []

    for item, odds in market_plan:
        rid = await next_id("market_bets")
        doc = {
            "id": rid,
            "user_id": user["id"],
            "market_id": item.marketId,
            "side": item.side,
            "stake_pln": Decimal("0") if is_parlay else stake,
            "odds": odds,
            "status": "pending",
            "created_at": now(),
            "slip_paid": False,
        }
        if is_parlay:
            doc["slip_group_id"] = slip_group_id
            doc["slip_stake_pln"] = stake
            doc["slip_potential_win"] = slip_potential
        await db.market_bets.insert_one(doc)
        placed_market.append(rid)

    for item, odds, w, price, end in crypto_plan:
        bet_id = await next_id("crypto_bets")
        solo_pot = (stake * odds).quantize(Decimal("0.01"))
        doc = {
            "id": bet_id,
            "user_id": user["id"],
            "window": item.window,
            "direction": item.direction,
            "stake_pln": Decimal("0") if is_parlay else stake,
            "odds": odds,
            "potential_win": slip_potential if is_parlay else solo_pot,
            "open_price": Decimal(str(w["openPrice"])),
            "entry_price": Decimal(str(price)),
            "settle_price": None,
            "window_start": w["windowStart"],
            "settle_at": end,
            "status": "pending",
            "created_at": now(),
            "settled_at": None,
            "slip_paid": False,
        }
        if is_parlay:
            doc["slip_group_id"] = slip_group_id
            doc["slip_stake_pln"] = stake
            doc["slip_potential_win"] = slip_potential
        await db.crypto_bets.insert_one(doc)
        placed_crypto.append(bet_id)

    await record_vip_wager(user["id"], stake)
    return {
        "ok": True,
        "slipGroupId": slip_group_id,
        "marketIds": placed_market,
        "cryptoIds": placed_crypto,
        "balance": float(updated["balance_pln"]),
    }


@router.post("")
async def place_slip(
    request: Request,
    payload: Slip,
    user: dict = Depends(get_current_user),
) -> dict:
    """Legacy per-leg stakes — prefer /parlay for a single combined stake."""
    await rate_limit_request(request, "user_bets.slip", 30)
    total = sum((Decimal(str(i.stakePln)) for i in payload.items), Decimal(0))
    if user["balance_pln"] < total:
        raise HTTPException(status_code=400, detail="insufficient balance")

    db = get_db()
    updated = await db.users.find_one_and_update(
        {"id": user["id"], "balance_pln": {"$gte": total}},
        {"$inc": {"balance_pln": -total}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="insufficient balance")

    placed: list[int] = []
    for item in payload.items:
        market = await db.markets.find_one({"id": item.marketId})
        if market is None or not is_open_for_betting(market):
            raise HTTPException(status_code=400, detail="market not available")
        odds = market["yes_odds"] if item.side == "yes" else market["no_odds"]
        rid = await next_id("market_bets")
        await db.market_bets.insert_one(
            {
                "id": rid,
                "user_id": user["id"],
                "market_id": item.marketId,
                "side": item.side,
                "stake_pln": item.stakePln,
                "odds": odds,
                "status": "pending",
                "created_at": now(),
            }
        )
        placed.append(rid)
    await record_vip_wager(user["id"], total)
    return {"ok": True, "slipIds": placed, "balance": float(updated["balance_pln"])}
