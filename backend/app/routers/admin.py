"""Admin / CRM endpoints."""
from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, model_validator

from ..auto_bets import create_bets_from_odds
from ..isports_api_client import IsportsNotConfiguredError
from ..isports_auto_bets import create_markets_from_variants, create_session, get_session_page
from ..isports_resolution import preview_isports_auto_resolve, resolve_isports_markets
from ..config import get_settings
from ..db import fetch_users_by_ids, get_db, next_id, now
from ..env_sync import mirror_market_patch, mirror_market_upsert, mirror_preset_delete, mirror_preset_upsert, mirror_to_peer
from ..market_bet_stats import bet_stats_by_market
from ..market_utils import format_event_date, market_bet_start_at, parse_iso_date
from ..market_settlement import settle_pending_market_bets
from ..mongo_sanitize import reject_operators
from ..preset_matching import apply_preset_to_eligible_markets, union_preset_names
from ..blik.settings_store import get_admin_flags
from ..blik.recipient_confirm import resend_withdraw_recipient_notify
from ..blik.service import admin_redeem_manual
from ..blik.types import BlikDepositStatus, BlikWithdrawStatus
from ..payments.types import PaymentStatus
from ..redeem_codes_service import create_redeem_code, serialize_code_row
from ..odds_api_client import list_sports
from ..rate_limit import limiter, rate_limit_request
from ..api_errors import http_400_from_value_error
from ..safe_url import normalize_username, validate_image_url_or_422
from ..session_cookies import clear_admin_session_cookies, set_admin_session_cookie
from ..security import (
    SESSION_TTL,
    constant_time_eq,
    generate_token,
    hash_token,
    require_admin,
    revoke_admin_session,
    verify_password,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminLoginBody(BaseModel):
    login: str = Field(min_length=1, max_length=64)
    pin: str = Field(min_length=1, max_length=16)
    password: str = Field(min_length=1, max_length=256)


def _verify_admin_credentials(login: str, pin: str, password: str) -> bool:
    s = get_settings()
    if not constant_time_eq(login.strip(), s.admin_login):
        return False
    if s.admin_uses_hashes:
        return verify_password(pin.strip(), s.admin_pin_hash) and verify_password(
            password, s.admin_password_hash
        )
    return constant_time_eq(pin.strip(), s.admin_pin) and constant_time_eq(
        password, s.admin_password
    )


@router.post("/login")
async def post_admin_login(request: Request, payload: AdminLoginBody) -> dict:
    await rate_limit_request(request, "admin.login", 15)
    ok = _verify_admin_credentials(payload.login, payload.pin, payload.password)
    if not ok:
        return {"ok": False, "error": "invalid"}
    token, token_hash = generate_token()
    await get_db().admin_sessions.insert_one(
        {
            "id": await next_id("admin_sessions"),
            "token_hash": token_hash,
            "created_at": now(),
            "expires_at": now() + SESSION_TTL,
        }
    )
    response = JSONResponse(content={"ok": True})
    set_admin_session_cookie(response, token, SESSION_TTL)
    return response


@router.post("/logout", dependencies=[Depends(require_admin)])
async def admin_logout(request: Request) -> JSONResponse:
    await revoke_admin_session(request)
    response = JSONResponse(content={"ok": True})
    clear_admin_session_cookies(response)
    return response


@router.post("/sessions/revoke-all", dependencies=[Depends(require_admin)])
async def admin_revoke_all_sessions() -> dict:
    await get_db().admin_sessions.delete_many({})
    return {"ok": True}


def _cutoff(range_key: str):
    days = {"today": 1, "7d": 7, "30d": 30}[range_key]
    return now() - timedelta(days=days)


def _blik_deposit_match(since=None) -> dict:
    match: dict = {"status": BlikDepositStatus.CONFIRMED.value}
    if since is not None:
        match["$expr"] = {"$gte": [{"$ifNull": ["$confirmed_at", "$created_at"]}, since]}
    return match


@router.get("/stats", dependencies=[Depends(require_admin)])
@limiter.limit("120/minute")
async def get_stats(
    request: Request,
    range: Literal["today", "7d", "30d"] = Query("today"),
) -> dict:
    db = get_db()
    since = _cutoff(range)
    new_users = await db.users.count_documents({"created_at": {"$gte": since}})
    active_users = len(await db.casino_rounds.distinct("user_id", {"created_at": {"$gte": since}}))
    dep_wallet = await db.wallet_ops.aggregate(
        [
            {"$match": {"kind": "deposit", "status": "completed", "created_at": {"$gte": since}}},
            {"$group": {"_id": None, "sum": {"$sum": "$amount_pln"}}},
        ]
    ).to_list(1)
    dep_crypto = await db.crypto_payments.aggregate(
        [
            {
                "$match": {
                    "kind": "deposit",
                    "status": "confirmed",
                    "created_at": {"$gte": since},
                }
            },
            {"$group": {"_id": None, "sum": {"$sum": {"$ifNull": ["$amount_pln", 0]}}}},
        ]
    ).to_list(1)
    dep_blik = await db.blik_deposits.aggregate(
        [
            {"$match": _blik_deposit_match(since)},
            {"$group": {"_id": None, "sum": {"$sum": "$amount_pln"}}},
        ]
    ).to_list(1)
    deposited = float(dep_wallet[0]["sum"]) if dep_wallet else 0.0
    deposited += float(dep_crypto[0]["sum"]) if dep_crypto else 0.0
    deposited += float(dep_blik[0]["sum"]) if dep_blik else 0.0
    cas = await db.casino_rounds.aggregate(
        [
            {"$match": {"created_at": {"$gte": since}}},
            {
                "$group": {
                    "_id": None,
                    "wagered": {"$sum": "$stake_pln"},
                    "profit": {"$sum": {"$subtract": ["$stake_pln", "$payout_pln"]}},
                }
            },
        ]
    ).to_list(1)
    wagered = float(cas[0]["wagered"]) if cas else 0.0
    profit = float(cas[0]["profit"]) if cas else 0.0
    rtp = round(((wagered - profit) / wagered * 100), 2) if wagered > 0 else 0
    return {
        "newUsers": new_users,
        "activeUsers": active_users,
        "deposited": deposited,
        "wagered": wagered,
        "profit": profit,
        "rtp": rtp,
    }


async def _casino_stats_by_user(db, user_ids: list[int]) -> dict[int, dict]:
    if not user_ids:
        return {}
    rows = await db.casino_rounds.aggregate(
        [
            {"$match": {"user_id": {"$in": user_ids}}},
            {
                "$group": {
                    "_id": "$user_id",
                    "wagered": {"$sum": "$stake_pln"},
                    "profit": {"$sum": {"$subtract": ["$stake_pln", "$payout_pln"]}},
                    "cnt": {"$sum": 1},
                }
            },
        ]
    ).to_list(len(user_ids))
    return {
        int(r["_id"]): {
            "wagered": float(r["wagered"]),
            "profit": float(r["profit"]),
            "cnt": int(r["cnt"]),
        }
        for r in rows
    }


@router.get("/users", dependencies=[Depends(require_admin)])
async def list_users() -> list[dict]:
    db = get_db()
    users = await db.users.find().sort("created_at", -1).limit(200).to_list(200)
    if not users:
        return []

    user_ids = [u["id"] for u in users]

    dep_crypto_rows = await db.crypto_payments.aggregate(
        [
            {
                "$match": {
                    "user_id": {"$in": user_ids},
                    "kind": "deposit",
                    "status": "confirmed",
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "sum": {"$sum": {"$ifNull": ["$amount_pln", 0]}},
                }
            },
        ]
    ).to_list(len(user_ids))
    dep_crypto = {int(r["_id"]): float(r["sum"]) for r in dep_crypto_rows}

    dep_wallet_rows = await db.wallet_ops.aggregate(
        [
            {
                "$match": {
                    "user_id": {"$in": user_ids},
                    "kind": "deposit",
                    "status": "completed",
                }
            },
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$amount_pln"}}},
        ]
    ).to_list(len(user_ids))
    dep_wallet = {int(r["_id"]): float(r["sum"]) for r in dep_wallet_rows}

    dep_blik_rows = await db.blik_deposits.aggregate(
        [
            {"$match": {**_blik_deposit_match(), "user_id": {"$in": user_ids}}},
            {"$group": {"_id": "$user_id", "sum": {"$sum": "$amount_pln"}}},
        ]
    ).to_list(len(user_ids))
    dep_blik = {int(r["_id"]): float(r["sum"]) for r in dep_blik_rows}

    casino_by_user = await _casino_stats_by_user(db, user_ids)

    mkt_rows = await db.market_bets.aggregate(
        [
            {"$match": {"user_id": {"$in": user_ids}}},
            {"$group": {"_id": "$user_id", "cnt": {"$sum": 1}}},
        ]
    ).to_list(len(user_ids))
    mkt_cnt = {int(r["_id"]): int(r["cnt"]) for r in mkt_rows}

    out = []
    for u in users:
        uid = u["id"]
        cas = casino_by_user.get(uid, {})
        wagered = cas.get("wagered", 0.0)
        casino_profit = cas.get("profit", 0.0)
        total_bets = cas.get("cnt", 0) + mkt_cnt.get(uid, 0)
        deposited = dep_crypto.get(uid, 0.0) + dep_wallet.get(uid, 0.0) + dep_blik.get(uid, 0.0)

        if u.get("discord_id") and u.get("telegram_id"):
            platform = "both"
        elif u.get("telegram_id"):
            platform = "telegram"
        elif u.get("discord_id"):
            platform = "discord"
        else:
            platform = "web"

        email = u.get("discord_id") or u.get("telegram_id") or "—"
        balance = u.get("balance_pln")
        if balance is None:
            balance = Decimal(0)

        out.append(
            {
                "username": u["username"],
                "email": str(email),
                "platform": platform,
                "status": "banned" if u.get("banned") else "active",
                "balance": float(balance),
                "deposited": deposited,
                "wagered": wagered,
                "totalBets": total_bets,
                "lifetimeProfit": -casino_profit,
                "joined": u["created_at"].strftime("%Y-%m-%d"),
                "lastActive": u["last_seen_at"].strftime("%Y-%m-%d %H:%M"),
                "ip": "—",
                "casinoOdds": (
                    round(float(u["casino_rtp"]) * 100, 2)
                    if u.get("casino_rtp") is not None
                    else None
                ),
            }
        )
    return out


class Status(BaseModel):
    status: Literal["active", "banned"]


class CasinoOddsBody(BaseModel):
    odds: Optional[float] = Field(default=None, ge=1, le=99)


@router.post("/users/{username}/status", dependencies=[Depends(require_admin)])
async def set_user_status(request: Request, username: str, payload: Status) -> dict:
    await rate_limit_request(request, "admin.user_status", 60)
    from ..authz import require_admin_target_username

    key = require_admin_target_username(username)
    result = await get_db().users.update_one(
        {"username": key},
        {"$set": {"banned": payload.status == "banned"}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="user not found")
    return {"ok": True}


@router.post("/users/{username}/casino-odds", dependencies=[Depends(require_admin)])
async def set_user_casino_odds(
    request: Request,
    username: str,
    payload: CasinoOddsBody,
) -> dict:
    await rate_limit_request(request, "admin.user_casino_odds", 60)
    from ..authz import require_admin_target_username

    key = require_admin_target_username(username)
    db = get_db()
    if payload.odds is None:
        result = await db.users.update_one(
            {"username": key},
            {"$unset": {"casino_rtp": ""}},
        )
    else:
        result = await db.users.update_one(
            {"username": key},
            {"$set": {"casino_rtp": round(payload.odds / 100.0, 4)}},
        )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="user not found")
    return {
        "ok": True,
        "casinoOdds": None if payload.odds is None else round(payload.odds, 2),
    }


def _payment_platform(u: dict) -> str:
    return "telegram" if u.get("telegram_id") else "discord"


def _admin_payment_status(status: str) -> str:
    if status == PaymentStatus.CONFIRMED.value:
        return "completed"
    if status == PaymentStatus.REFUNDED.value:
        return "refunded"
    if status in (PaymentStatus.EXPIRED.value, PaymentStatus.FAILED.value):
        return "failed"
    return "pending"


def _blik_admin_status(status: str) -> str:
    if status == BlikDepositStatus.CONFIRMED.value:
        return "completed"
    if status in (BlikDepositStatus.FAILED.value, BlikDepositStatus.EXPIRED.value, BlikDepositStatus.PROOF_REJECTED.value):
        return "failed"
    return "pending"


@router.get("/transactions", dependencies=[Depends(require_admin)])
async def list_transactions(
    kind: Optional[Literal["deposit", "withdraw"]] = Query(None),
) -> list[dict]:
    db = get_db()
    out: list[dict] = []
    crypto_deps: list[dict] = []
    blik_deps: list[dict] = []
    crypto_wd: list[dict] = []
    blik_wd: list[dict] = []

    if kind in (None, "deposit"):
        crypto_deps = await db.crypto_payments.find({"kind": "deposit"}).sort("created_at", -1).limit(150).to_list(150)
        blik_deps = await db.blik_deposits.find().sort("created_at", -1).limit(100).to_list(100)

    if kind in (None, "withdraw"):
        crypto_wd = await db.crypto_payments.find({"kind": "withdraw"}).sort("created_at", -1).limit(150).to_list(150)
        blik_wd = await db.blik_withdrawals.find().sort("created_at", -1).limit(100).to_list(100)

    user_ids: list[int] = []
    for rows in (crypto_deps, blik_deps, crypto_wd, blik_wd):
        user_ids.extend(p["user_id"] for p in rows if p.get("user_id") is not None)
    users_map = await fetch_users_by_ids(db, user_ids)

    if kind in (None, "deposit"):
        for p in crypto_deps:
            u = users_map.get(p["user_id"]) if p.get("user_id") else None
            username = u["username"] if u else "—"
            platform = _payment_platform(u) if u else "—"
            amount_crypto = float(p["amount_expected"])
            amount_pln = float(p["amount_pln"]) if p.get("amount_pln") is not None else None
            out.append({
                "id": f"cp_{p['id']}",
                "paymentId": p["id"],
                "user": username,
                "type": "deposit",
                "method": "crypto",
                "asset": p["asset"],
                "amount": amount_pln if amount_pln is not None else amount_crypto,
                "amountCrypto": amount_crypto,
                "amountPln": amount_pln,
                "platform": platform,
                "status": _admin_payment_status(p["status"]),
                "date": p["created_at"].strftime("%Y-%m-%d %H:%M"),
                "address": p.get("address"),
                "matchedWithdraw": p.get("matched_withdraw_id"),
                "fundsWithdrawal": bool(p.get("funds_user_address")),
            })

        for p in blik_deps:
            u = users_map.get(p["user_id"])
            username = u["username"] if u else "—"
            amount_pln = float(p["amount_pln"])
            is_manual = p.get("flow") == "manual_code"
            out.append({
                "id": f"blik_d_{p['id']}",
                "paymentId": p["id"],
                "user": username,
                "type": "deposit",
                "method": "blik",
                "asset": "BLIK",
                "amount": amount_pln,
                "amountPln": amount_pln,
                "platform": p.get("platform", "—"),
                "status": _blik_admin_status(p["status"]),
                "blikStatus": p["status"],
                "flow": p.get("flow"),
                "blikManual": is_manual,
                "manualCode": p.get("manual_code"),
                "matchedWithdraw": p.get("matched_withdraw_id"),
                "date": p["created_at"].strftime("%Y-%m-%d %H:%M"),
            })

    if kind in (None, "withdraw"):
        for p in crypto_wd:
            u = users_map.get(p["user_id"]) if p.get("user_id") else None
            username = u["username"] if u else "—"
            platform = _payment_platform(u) if u else "—"
            amount_crypto = float(p["amount_expected"])
            amount_pln = float(p["amount_pln"]) if p.get("amount_pln") is not None else None
            filled = float(p.get("amount_filled") or 0)
            out.append({
                "id": f"cp_{p['id']}",
                "paymentId": p["id"],
                "user": username,
                "type": "withdraw",
                "method": "crypto",
                "asset": p["asset"],
                "amount": amount_pln if amount_pln is not None else amount_crypto,
                "amountCrypto": amount_crypto,
                "amountPln": amount_pln,
                "platform": platform,
                "status": _admin_payment_status(p["status"]),
                "date": p["created_at"].strftime("%Y-%m-%d %H:%M"),
                "destination": p.get("destination_address"),
                "filled": filled,
                "remaining": max(amount_crypto - filled, 0),
            })

        for p in blik_wd:
            u = users_map.get(p["user_id"])
            username = u["username"] if u else "—"
            st = p["status"]
            if st == BlikWithdrawStatus.REFUNDED.value:
                admin_st = "refunded"
            elif st == BlikWithdrawStatus.FULFILLED.value:
                admin_st = "completed"
            elif st == BlikWithdrawStatus.CANCELLED.value:
                admin_st = "failed"
            else:
                admin_st = "pending"
            out.append({
                "id": f"blik_w_{p['id']}",
                "paymentId": p["id"],
                "user": username,
                "type": "withdraw",
                "method": "blik",
                "asset": "BLIK",
                "amount": float(p["amount_pln"]),
                "amountPln": float(p["amount_pln"]),
                "platform": p.get("platform", "—"),
                "status": admin_st,
                "blikStatus": st,
                "destination": p.get("phone"),
                "matchedDeposit": p.get("matched_deposit_id"),
                "date": p["created_at"].strftime("%Y-%m-%d %H:%M"),
            })

    out.sort(key=lambda x: x["date"], reverse=True)
    return out[:250]


class RefundWithdrawBody(BaseModel):
    id: str = Field(min_length=1, max_length=64)


async def _unlink_blik_deposit_for_withdraw(withdraw_id: int, deposit_id: int | None) -> None:
    db = get_db()
    if deposit_id:
        dep = await db.blik_deposits.find_one({"id": deposit_id})
        if dep and dep["status"] not in (
            BlikDepositStatus.CONFIRMED.value,
            BlikDepositStatus.FAILED.value,
        ):
            await db.blik_deposits.update_one(
                {"id": deposit_id},
                {
                    "$set": {
                        "status": BlikDepositStatus.EXPIRED.value,
                        "matched_withdraw_id": None,
                        "updated_at": now(),
                    }
                },
            )
        return
    cursor = db.blik_deposits.find({"matched_withdraw_id": withdraw_id})
    async for dep in cursor:
        if dep["status"] in (
            BlikDepositStatus.CONFIRMED.value,
            BlikDepositStatus.FAILED.value,
        ):
            continue
        await db.blik_deposits.update_one(
            {"id": dep["id"]},
            {
                "$set": {
                    "status": BlikDepositStatus.EXPIRED.value,
                    "matched_withdraw_id": None,
                    "updated_at": now(),
                }
            },
        )


@router.post("/withdrawals/refund", dependencies=[Depends(require_admin)])
async def refund_withdrawal(body: RefundWithdrawBody) -> dict:
    raw = body.id.strip()
    db = get_db()

    if raw.startswith("cp_"):
        try:
            payment_id = int(raw[3:])
        except ValueError as e:
            raise HTTPException(status_code=400, detail="invalid_id") from e
        doc = await db.crypto_payments.find_one(
            {"id": payment_id, "kind": "withdraw"},
        )
        if not doc:
            raise HTTPException(status_code=404, detail="not_found")
        if doc["status"] == PaymentStatus.REFUNDED.value:
            return {"ok": True, "status": "refunded", "alreadyRefunded": True}
        if doc["status"] == PaymentStatus.CONFIRMED.value:
            raise HTTPException(status_code=400, detail="withdraw_completed")
        user_id = doc.get("user_id")
        amount_pln = doc.get("amount_pln")
        if user_id is None or amount_pln is None:
            raise HTTPException(status_code=400, detail="no_balance_to_refund")
        pln = Decimal(str(amount_pln))
        await db.users.update_one({"id": user_id}, {"$inc": {"balance_pln": pln}})
        await db.crypto_payments.update_one(
            {"id": payment_id},
            {"$set": {"status": PaymentStatus.REFUNDED.value, "updated_at": now()}},
        )
        return {"ok": True, "status": "refunded", "amountPln": float(pln)}

    if raw.startswith("blik_w_"):
        try:
            withdraw_id = int(raw[7:])
        except ValueError as e:
            raise HTTPException(status_code=400, detail="invalid_id") from e
        doc = await db.blik_withdrawals.find_one({"id": withdraw_id})
        if not doc:
            raise HTTPException(status_code=404, detail="not_found")
        if doc["status"] == BlikWithdrawStatus.REFUNDED.value:
            return {"ok": True, "status": "refunded", "alreadyRefunded": True}
        if doc["status"] == BlikWithdrawStatus.FULFILLED.value:
            raise HTTPException(status_code=400, detail="withdraw_completed")
        pln = Decimal(str(doc["amount_pln"]))
        await _unlink_blik_deposit_for_withdraw(
            withdraw_id,
            doc.get("matched_deposit_id"),
        )
        await db.users.update_one(
            {"id": doc["user_id"]},
            {"$inc": {"balance_pln": pln}},
        )
        await db.blik_withdrawals.update_one(
            {"id": withdraw_id},
            {
                "$set": {
                    "status": BlikWithdrawStatus.REFUNDED.value,
                    "matched_deposit_id": None,
                    "updated_at": now(),
                }
            },
        )
        return {"ok": True, "status": "refunded", "amountPln": float(pln)}

    raise HTTPException(status_code=400, detail="invalid_id")


@router.get("/settings", dependencies=[Depends(require_admin)])
async def admin_get_settings() -> dict:
    return await get_admin_flags()


class SettingsPatch(BaseModel):
    blikActive: Optional[bool] = None
    siteUnavailable: Optional[bool] = None


@router.patch("/settings", dependencies=[Depends(require_admin)])
async def admin_patch_settings(payload: SettingsPatch) -> dict:
    from ..blik.settings_store import set_blik_active, set_site_unavailable

    if payload.blikActive is not None:
        await set_blik_active(payload.blikActive)
    if payload.siteUnavailable is not None:
        await set_site_unavailable(payload.siteUnavailable)
    return await get_admin_flags()


@router.get("/blik/pending-codes", dependencies=[Depends(require_admin)])
async def list_pending_blik_codes() -> list[dict]:
    db = get_db()
    rows = await db.blik_deposits.find(
        {"status": BlikDepositStatus.MANUAL_SUBMITTED.value, "flow": "manual_code"}
    ).sort("created_at", -1).limit(50).to_list(50)
    users_map = await fetch_users_by_ids(db, [p["user_id"] for p in rows])
    out = []
    for p in rows:
        u = users_map.get(p["user_id"])
        out.append({
            "id": p["id"],
            "user": u["username"] if u else "—",
            "amountPln": float(p["amount_pln"]),
            "code": p.get("manual_code"),
            "platform": p.get("platform"),
            "date": p["created_at"].strftime("%Y-%m-%d %H:%M"),
        })
    return out


class BlikRedeem(BaseModel):
    success: bool
    note: Optional[str] = None


@router.post("/blik/deposits/{deposit_id}/redeem", dependencies=[Depends(require_admin)])
async def redeem_blik_code(deposit_id: int, payload: BlikRedeem) -> dict:
    return await admin_redeem_manual(deposit_id, payload.success, payload.note)


@router.post(
    "/blik/deposits/{deposit_id}/resend-recipient-notify",
    dependencies=[Depends(require_admin)],
)
async def resend_blik_recipient_notify(deposit_id: int) -> dict:
    return await resend_withdraw_recipient_notify(deposit_id)


@router.get("/bets", dependencies=[Depends(require_admin)])
async def list_bets() -> list[dict]:
    rows = await get_db().markets.find().sort("created_at", -1).limit(200).to_list(200)
    stats = await bet_stats_by_market([str(r["id"]) for r in rows])
    out = []
    for r in rows:
        mid = str(r["id"])
        s = stats.get(mid, {})
        out.append(
            {
                "id": r["id"],
                "title": r["title"],
                "image": r.get("image"),
                "eventDate": format_event_date(market_bet_start_at(r)),
                "yesLabel": r.get("yes_label", "Yes"),
                "noLabel": r.get("no_label", "No"),
                "yes": float(r["yes_odds"]),
                "no": float(r["no_odds"]),
                "status": r["status"],
                "outcome": r.get("outcome"),
                "source": r.get("source"),
                "autoResolve": bool(r.get("auto_resolve")),
                "bets": int(s.get("bet_count", 0)),
                "volume": float(s.get("money", 0)),
            }
        )
    return out


@router.get("/bet-placements", dependencies=[Depends(require_admin)])
async def list_bet_placements() -> list[dict]:
    db = get_db()
    bets = await db.market_bets.find().sort("created_at", -1).limit(200).to_list(200)
    users_map = await fetch_users_by_ids(db, [b["user_id"] for b in bets])
    out = []
    for b in bets:
        u = users_map.get(b["user_id"])
        if not u:
            continue
        out.append(
            {
                "id": f"px_{b['id']}",
                "user": u["username"],
                "market": b["market_id"],
                "side": b["side"],
                "stake": float(b["stake_pln"]),
                "odds": float(b["odds"]),
                "date": b["created_at"].strftime("%Y-%m-%d %H:%M"),
            }
        )
    return out


class CreateBet(BaseModel):
    id: Optional[str] = Field(default=None, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    image: Optional[str] = None
    yesLabel: str = "Yes"
    noLabel: str = "No"
    yes: Decimal = Field(gt=0, max_digits=10, decimal_places=4)
    no: Decimal = Field(gt=0, max_digits=10, decimal_places=4)
    eventDate: Optional[str] = None


class UpdateBet(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=256)
    image: Optional[str] = None
    yesLabel: Optional[str] = Field(default=None, min_length=1, max_length=128)
    noLabel: Optional[str] = Field(default=None, min_length=1, max_length=128)
    yes: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=4)
    no: Optional[Decimal] = Field(default=None, gt=0, max_digits=10, decimal_places=4)
    eventDate: Optional[str] = None


@router.post("/bets", dependencies=[Depends(require_admin)])
async def create_bet(payload: CreateBet) -> dict:
    bet_id = (payload.id or "").strip() or f"market-{await next_id('markets')}"
    event_date = parse_iso_date(payload.eventDate) if payload.eventDate else None
    image = validate_image_url_or_422(payload.image)
    market_doc = {
        "id": bet_id,
        "title": payload.title,
        "image": image,
        "yes_label": payload.yesLabel,
        "no_label": payload.noLabel,
        "yes_odds": payload.yes,
        "no_odds": payload.no,
        "status": "active",
        "outcome": None,
        "created_at": now(),
        "event_date": event_date,
    }
    await get_db().markets.insert_one(market_doc)
    await mirror_to_peer(mirror_market_upsert(market_doc))
    return {"ok": True, "id": bet_id}


@router.patch("/bets/{bet_id}", dependencies=[Depends(require_admin)])
async def update_bet(bet_id: str, payload: UpdateBet) -> dict:
    db = get_db()
    market = await db.markets.find_one({"id": bet_id})
    if market is None:
        raise HTTPException(status_code=404, detail="not found")
    patch: dict = {}
    if payload.title is not None:
        patch["title"] = payload.title
    if payload.image is not None:
        patch["image"] = validate_image_url_or_422(payload.image) if payload.image else None
    if payload.yesLabel is not None:
        patch["yes_label"] = payload.yesLabel
    if payload.noLabel is not None:
        patch["no_label"] = payload.noLabel
    if payload.yes is not None:
        patch["yes_odds"] = payload.yes
    if payload.no is not None:
        patch["no_odds"] = payload.no
    if payload.eventDate is not None:
        patch["event_date"] = parse_iso_date(payload.eventDate)
    if not patch:
        return {"ok": True, "id": bet_id}
    await db.markets.update_one({"id": bet_id}, {"$set": patch})
    await mirror_to_peer(mirror_market_patch(bet_id, patch))
    return {"ok": True, "id": bet_id}


class AutoBets(BaseModel):
    sport: str = Field(min_length=1, max_length=64)
    amount: int = Field(ge=1, le=20)


@router.get("/odds/sports", dependencies=[Depends(require_admin)])
async def odds_sports() -> list[dict]:
    try:
        rows = await list_sports()
    except ValueError:
        raise HTTPException(status_code=503, detail="odds_api_not_configured") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail="odds_api_error") from exc
    return [{"name": r.get("name", ""), "slug": r.get("slug", "")} for r in rows if r.get("slug")]


@router.post("/bets/auto", dependencies=[Depends(require_admin)])
async def auto_create_bets(payload: AutoBets) -> dict:
    try:
        return await create_bets_from_odds(payload.sport.strip(), payload.amount)
    except ValueError:
        raise HTTPException(status_code=503, detail="odds_api_not_configured") from None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="odds_api_error") from exc


class IsportsSession(BaseModel):
    sport: str = Field(default="football", max_length=32)
    amount: int = Field(default=5, ge=1, le=20)


class IsportsCreate(BaseModel):
    matchId: str = Field(min_length=1, max_length=64)
    variants: list[str] = Field(min_length=1, max_length=20)


@router.post("/isports/sessions", dependencies=[Depends(require_admin)])
async def isports_create_session(payload: IsportsSession) -> dict:
    try:
        return await create_session(payload.sport.strip(), payload.amount)
    except HTTPException:
        raise
    except IsportsNotConfiguredError:
        raise HTTPException(status_code=503, detail="isports_api_not_configured") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail="isports_api_error") from exc


@router.get("/isports/sessions/{session_id}", dependencies=[Depends(require_admin)])
async def isports_session_page(
    session_id: str,
    page: int = Query(0, ge=0),
    perPage: int = Query(1, ge=1, le=1),
) -> dict:
    try:
        return await get_session_page(session_id, page, perPage)
    except HTTPException:
        raise
    except IsportsNotConfiguredError:
        raise HTTPException(status_code=503, detail="isports_api_not_configured") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail="isports_api_error") from exc


@router.post("/isports/sessions/{session_id}/create", dependencies=[Depends(require_admin)])
async def isports_session_create(session_id: str, payload: IsportsCreate) -> dict:
    try:
        return await create_markets_from_variants(session_id, payload.matchId, payload.variants)
    except HTTPException:
        raise
    except IsportsNotConfiguredError:
        raise HTTPException(status_code=503, detail="isports_api_not_configured") from None
    except Exception as exc:
        raise HTTPException(status_code=502, detail="isports_api_error") from exc


@router.get("/isports/auto-resolve/preview", dependencies=[Depends(require_admin)])
async def isports_auto_resolve_preview() -> dict:
    """Count active auto-resolve markets whose event time has passed."""
    return await preview_isports_auto_resolve()


@router.post("/isports/auto-resolve", dependencies=[Depends(require_admin)])
async def isports_auto_resolve() -> dict:
    """Run iSports auto-resolve now (only markets whose event time has passed)."""
    try:
        result = await resolve_isports_markets(only_event_ended=True)
    except IsportsNotConfiguredError:
        raise HTTPException(status_code=503, detail="isports_api_not_configured") from None
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail="isports_api_error") from exc
    return {"ok": True, **result}


class Resolve(BaseModel):
    outcome: Literal["yes", "no", "cashback", "draw"]


@router.post("/bets/{bet_id}/resolve", dependencies=[Depends(require_admin)])
async def resolve_bet(bet_id: str, payload: Resolve) -> dict:
    db = get_db()
    market = await db.markets.find_one({"id": bet_id})
    if market is None:
        raise HTTPException(status_code=404, detail="not found")
    if market["status"] in ("resolved", "cancelled"):
        return {"ok": True}

    await db.markets.update_one(
        {"id": bet_id},
        {"$set": {"status": "resolved", "outcome": payload.outcome}},
    )
    await settle_pending_market_bets(bet_id, payload.outcome)
    return {"ok": True}


@router.delete("/bets/{bet_id}", dependencies=[Depends(require_admin)])
async def delete_bet(bet_id: str) -> dict:
    db = get_db()
    market = await db.markets.find_one({"id": bet_id})
    if market is None:
        raise HTTPException(status_code=404, detail="not found")
    if market["status"] == "cancelled":
        return {"ok": True, "refundedCount": 0}

    refunded = 0
    if market["status"] == "active":
        refunded = await settle_pending_market_bets(bet_id, "cashback")

    await db.markets.update_one(
        {"id": bet_id},
        {"$set": {"status": "cancelled", "outcome": "cashback"}},
    )
    return {"ok": True, "refundedCount": refunded}


async def _game_aggregates(games: list[str]) -> dict:
    db = get_db()
    pipeline = [
        {"$match": {"game": {"$in": games}}},
        {
            "$group": {
                "_id": "$game",
                "plays": {"$sum": 1},
                "wagered": {"$sum": "$stake_pln"},
                "profit": {"$sum": {"$subtract": ["$stake_pln", "$payout_pln"]}},
            }
        },
    ]
    rows = await db.casino_rounds.aggregate(pipeline).to_list(len(games))
    by_game = {r["_id"]: r for r in rows}
    summary = []
    total_plays = 0
    total_wager = Decimal(0)
    total_profit = Decimal(0)
    for g in games:
        r = by_game.get(g)
        plays = r["plays"] if r else 0
        wager = Decimal(str(r["wagered"])) if r else Decimal(0)
        profit = Decimal(str(r["profit"])) if r else Decimal(0)
        rtp = round(float((wager - profit) / wager) * 100, 2) if wager > 0 else 0
        summary.append({
            "name": g, "plays": plays, "rtp": rtp,
            "wagered": float(wager), "profit": float(profit),
        })
        total_plays += plays
        total_wager += wager
        total_profit += profit

    tx_rows: list[dict] = []
    tx_raw = await db.casino_rounds.find({"game": {"$in": games}}).sort("created_at", -1).limit(50).to_list(50)
    users_map = await fetch_users_by_ids(db, [t["user_id"] for t in tx_raw])
    for t in tx_raw:
        u = users_map.get(t["user_id"])
        if u:
            tx_rows.append({**t, "username": u["username"]})

    total_rtp = round(float((total_wager - total_profit) / total_wager) * 100, 2) if total_wager > 0 else 0
    return {
        "games": summary,
        "transactions": [
            {
                "id": f"gt_{t['id']}", "user": t["username"], "game": t["game"],
                "bet": float(t["stake_pln"]), "win": float(t["payout_pln"]),
                "date": t["created_at"].strftime("%Y-%m-%d %H:%M"),
            }
            for t in tx_rows
        ],
        "totals": {
            "plays": total_plays, "rtp": total_rtp,
            "wagered": float(total_wager), "profit": float(total_profit),
        },
    }


@router.get("/games/crypto", dependencies=[Depends(require_admin)])
async def get_krypto() -> dict:
    db = get_db()
    pipeline = [
        {
            "$group": {
                "_id": "$window",
                "plays": {"$sum": 1},
                "wagered": {"$sum": "$stake_pln"},
                "profit": {
                    "$sum": {
                        "$cond": [
                            {"$eq": ["$status", "won"]},
                            {"$subtract": ["$potential_win", "$stake_pln"]},
                            {"$multiply": ["$stake_pln", -1]},
                        ]
                    }
                },
            }
        }
    ]
    rows = await db.crypto_bets.aggregate(pipeline).to_list(10)
    games = [
        {
            "name": f"BTC {r['_id']}",
            "plays": r["plays"],
            "wagered": float(r["wagered"]),
            "profit": -float(r["profit"]),
        }
        for r in rows
    ]
    tx_raw = await db.crypto_bets.find().sort("created_at", -1).limit(50).to_list(50)
    users_map = await fetch_users_by_ids(db, [t["user_id"] for t in tx_raw])
    tx_out = []
    for t in tx_raw:
        u = users_map.get(t["user_id"])
        if u:
            tx_out.append({**t, "username": u["username"]})
    return {
        "games": games,
        "transactions": [
            {
                "id": f"kt_{t['id']}",
                "user": t["username"],
                "game": f"BTC {t['window']}",
                "bet": float(t["stake_pln"]),
                "win": float(t["potential_win"]) if t["status"] == "won" else 0,
                "date": t["created_at"].strftime("%Y-%m-%d %H:%M"),
            }
            for t in tx_out
        ],
        "totals": {
            "plays": sum(g["plays"] for g in games),
            "wagered": sum(g["wagered"] for g in games),
            "profit": sum(g["profit"] for g in games),
        },
    }


@router.get("/games/casino", dependencies=[Depends(require_admin)])
async def get_kasyno() -> dict:
    return await _game_aggregates(["limbo", "dice", "keno", "crash", "blackjack", "blitz"])


class PresetCreate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=128)
    payload: Optional[dict] = None
    imageUrl: Optional[str] = None
    names: Optional[list[str]] = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def _reject_mongo_operators_in_payload(self) -> "PresetCreate":
        if self.payload is not None:
            reject_operators(self.payload)
        return self

    def resolve(self) -> tuple[str, dict]:
        if self.payload is not None and self.name:
            return self.name.strip(), self.payload
        names = [str(n).strip() for n in (self.names or []) if str(n).strip()]
        if not names or not self.imageUrl:
            raise ValueError("names and imageUrl required")
        preset_name = (self.name or names[0]).strip() or names[0]
        return preset_name, {"imageUrl": self.imageUrl, "names": names}


def _preset_list_filter(
    q: Optional[str],
    codes: Literal["all", "single", "multi"],
) -> dict:
    filt: dict = {}
    if q and q.strip():
        escaped = re.escape(q.strip())
        filt["$or"] = [
            {"name": {"$regex": escaped, "$options": "i"}},
            {"payload.names": {"$regex": escaped, "$options": "i"}},
        ]
    if codes == "single":
        filt["payload.names.1"] = {"$exists": False}
        filt["payload.names.0"] = {"$exists": True}
    elif codes == "multi":
        filt["payload.names.1"] = {"$exists": True}
    return filt


@router.get("/presets", dependencies=[Depends(require_admin)])
async def list_presets(
    q: Optional[str] = Query(None, max_length=128),
    codes: Literal["all", "single", "multi"] = Query("all"),
) -> list[dict]:
    filt = _preset_list_filter(q, codes)
    rows = await get_db().presets.find(filt).sort("created_at", -1).to_list(500)
    return [
        {"id": r["id"], "name": r["name"], **r["payload"],
         "createdAt": r["created_at"].strftime("%Y-%m-%d")}
        for r in rows
    ]


@router.post("/presets", dependencies=[Depends(require_admin)])
async def create_preset(request: Request, payload: PresetCreate) -> dict:
    await rate_limit_request(request, "admin.preset_create", 60)
    try:
        preset_name, payload = payload.resolve()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid preset") from exc

    names = payload.get("names") or []
    image_url = validate_image_url_or_422(payload.get("imageUrl"), field="imageUrl")
    if not image_url or not names:
        raise HTTPException(status_code=422, detail="invalid preset")
    payload = {**payload, "imageUrl": image_url}

    preset_id = await next_id("presets")
    created = now()
    await get_db().presets.insert_one(
        {"id": preset_id, "name": preset_name, "payload": payload, "created_at": created}
    )

    applied = await apply_preset_to_eligible_markets(str(image_url), names)

    await mirror_to_peer(
        mirror_preset_upsert(
            preset_name=preset_name,
            payload=payload,
            refresh_existing=False,
        )
    )

    return {
        "id": preset_id,
        "name": preset_name,
        **payload,
        "createdAt": created.strftime("%Y-%m-%d"),
        "appliedTo": applied,
        "appliedCount": len(applied),
    }


@router.patch("/presets/{preset_id}", dependencies=[Depends(require_admin)])
async def update_preset(
    request: Request, preset_id: int, body: PresetCreate
) -> dict:
    await rate_limit_request(request, "admin.preset_update", 60)
    row = await get_db().presets.find_one({"id": preset_id})
    if not row:
        raise HTTPException(status_code=404, detail="preset not found")
    try:
        preset_name, payload = body.resolve()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="invalid preset") from exc

    names = payload.get("names") or []
    image_url = validate_image_url_or_422(payload.get("imageUrl"), field="imageUrl")
    if not image_url or not names:
        raise HTTPException(status_code=422, detail="invalid preset")
    payload = {**payload, "imageUrl": image_url}

    old_payload = row.get("payload") or {}
    old_names = list(old_payload.get("names") or [])
    match_names = union_preset_names(
        names,
        old_names,
        preset_name,
        row.get("name"),
    )

    await get_db().presets.update_one(
        {"id": preset_id},
        {"$set": {"name": preset_name, "payload": payload}},
    )

    applied = await apply_preset_to_eligible_markets(
        str(image_url),
        match_names,
        refresh_existing=True,
    )

    await mirror_to_peer(
        mirror_preset_upsert(
            preset_name=preset_name,
            payload=payload,
            refresh_existing=True,
        )
    )

    created_at = row.get("created_at")
    return {
        "id": preset_id,
        "name": preset_name,
        **payload,
        "createdAt": created_at.strftime("%Y-%m-%d") if created_at else "",
        "appliedTo": applied,
        "appliedCount": len(applied),
    }


@router.delete("/presets/{preset_id}", dependencies=[Depends(require_admin)])
async def delete_preset(preset_id: int) -> dict:
    row = await get_db().presets.find_one({"id": preset_id})
    if not row:
        raise HTTPException(status_code=404, detail="preset not found")
    old_payload = row.get("payload") or {}
    preset_name = str(row.get("name") or "")
    names = list(old_payload.get("names") or [])
    result = await get_db().presets.delete_one({"id": preset_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="preset not found")
    await mirror_to_peer(mirror_preset_delete(preset_name=preset_name, names=names))
    return {"ok": True}


# ── Promo codes (Kody) ───────────────────────────────────────────────────────

@router.get("/codes", dependencies=[Depends(require_admin)])
async def list_codes() -> list[dict]:
    rows = await get_db().redeem_codes.find().sort("created_at", -1).limit(500).to_list(500)
    return [serialize_code_row(r) for r in rows]


class CreateCode(BaseModel):
    amountPln: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    maxUses: int = Field(ge=1, le=1_000_000)
    label: Optional[str] = Field(default=None, max_length=128)


@router.post("/codes", dependencies=[Depends(require_admin)])
async def create_code(payload: CreateCode) -> dict:
    try:
        doc = await create_redeem_code(
            payload.amountPln,
            payload.maxUses,
            kind="admin",
            label=payload.label or "Admin",
        )
    except ValueError as e:
        raise http_400_from_value_error(e) from e
    row = serialize_code_row(doc)
    return {"ok": True, **row}


class DailyCodeSettingsPatch(BaseModel):
    amountPln: float = Field(gt=0)
    maxUses: int = Field(ge=1, le=1_000_000)


@router.get("/codes/daily-settings", dependencies=[Depends(require_admin)])
async def get_daily_code_settings() -> dict:
    from ..blik.settings_store import get_daily_code_config

    return await get_daily_code_config()


@router.patch("/codes/daily-settings", dependencies=[Depends(require_admin)])
async def patch_daily_code_settings(payload: DailyCodeSettingsPatch) -> dict:
    from ..blik.settings_store import set_daily_code_config

    try:
        return await set_daily_code_config(payload.amountPln, payload.maxUses)
    except ValueError as e:
        raise http_400_from_value_error(e) from e
