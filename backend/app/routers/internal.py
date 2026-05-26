"""Bot-only endpoints — guarded by HMAC `x-internal-secret`.

Telegram / Discord bots register users and issue OTPs.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Literal, Optional
from decimal import Decimal

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..db import get_db, next_id, now
from ..distributed_rate import enforce_distributed_rate
from ..rate_limit import get_remote_address, rate_limit_request
from ..config import get_settings
from ..redeem_codes_service import create_redeem_code
from ..rewards_service import signup_vip_bonus_claims
from ..security import (
    OTP_TTL,
    generate_otp,
    generate_pass_key,
    generate_password,
    generate_username,
    hash_password,
    require_internal,
    verify_password,
)

router = APIRouter(prefix="/api/auth/internal", tags=["internal"], dependencies=[Depends(require_internal)])


NICK_REWARD_PLN = Decimal("2.50")
NICK_REWARD_COOLDOWN = timedelta(hours=24)


def _new_user_fields(
    *,
    username: str,
    password_hash: str,
    pass_key_hash: str,
    telegram_id: str | None,
    discord_id: str | None,
    referred_by_id: int | None = None,
) -> dict:
    fields = {
        "username": username.lower(),
        "password_hash": password_hash,
        "pass_key_hash": pass_key_hash,
        "balance_pln": Decimal("0.00"),
        "banned": False,
        "last_nick_reward_at": None,
        "referred_by_id": referred_by_id,
        "vip_wagered_pln": Decimal("0"),
        "vip_won_pln": Decimal("0"),
        "playthrough_base_pln": Decimal("0"),
        "playthrough_wagered_pln": Decimal("0"),
        "vip_period_stats": {},
        "vip_rank_claimed_tiers": [],
        "vip_bonus_claims": signup_vip_bonus_claims(),
        "referral_claimed_tiers": [],
        "created_at": now(),
        "last_seen_at": now(),
    }
    if telegram_id is not None:
        fields["telegram_id"] = telegram_id
    if discord_id is not None:
        fields["discord_id"] = discord_id
    return fields


async def _resolve_referrer_id(ref_username: str | None) -> int | None:
    from ..safe_url import normalize_username

    ref_key = normalize_username(ref_username)
    if not ref_key:
        return None
    referrer = await get_db().users.find_one({"username": ref_key}, {"id": 1})
    return referrer["id"] if referrer else None


async def _allocate_unique_username() -> str:
    for _ in range(40):
        candidate = generate_username()
        exists = await get_db().users.find_one({"username": candidate}, {"_id": 1})
        if not exists:
            return candidate
    raise HTTPException(status_code=500, detail="cannot allocate username")


def _otp_lookup_key(provider: str, code: str) -> str:
    return hashlib.sha256(f"{provider}:{code}".encode("utf-8")).hexdigest()


async def _issue_otp(user_id: int, provider: str) -> str:
    code = generate_otp()
    code_hash = hash_password(code)
    lookup_key = _otp_lookup_key(provider, code)
    db = get_db()
    await db.otp_codes.update_many(
        {"user_id": user_id, "used_at": None},
        {"$set": {"used_at": now()}},
    )
    await db.otp_codes.insert_one(
        {
            "id": await next_id("otp_codes"),
            "user_id": user_id,
            "provider": provider,
            "code_hash": code_hash,
            "lookup_key": lookup_key,
            "expires_at": now() + OTP_TTL,
            "used_at": None,
        }
    )
    return code


# ── Telegram ─────────────────────────────────────────────────────────────────

class TelegramRegisterBody(BaseModel):
    telegramId: str = Field(min_length=1, max_length=64)
    refUsername: Optional[str] = Field(default=None, max_length=64)


@router.post("/register")
async def telegram_register(request: Request, payload: TelegramRegisterBody) -> dict:
    await rate_limit_request(request, "internal.telegram_register", 30)
    existing = await get_db().users.find_one({"telegram_id": payload.telegramId})
    if existing:
        return {"exists": True, "username": existing["username"]}

    username = await _allocate_unique_username()
    password = generate_password()
    pass_key = generate_pass_key()
    user_id = await next_id("users")
    referred_by_id = await _resolve_referrer_id(payload.refUsername)
    await get_db().users.insert_one(
        {
            "id": user_id,
            **_new_user_fields(
                username=username,
                password_hash=hash_password(password),
                pass_key_hash=hash_password(pass_key),
                telegram_id=payload.telegramId,
                discord_id=None,
                referred_by_id=referred_by_id,
            ),
        }
    )
    return {
        "exists": False,
        "username": username,
        "password": password,
        "passKey": pass_key,
    }


# ── Discord ──────────────────────────────────────────────────────────────────

class DiscordRegisterBody(BaseModel):
    discordId: str = Field(min_length=1, max_length=64)
    refUsername: Optional[str] = Field(default=None, max_length=64)


@router.post("/discord/register")
async def discord_register(request: Request, payload: DiscordRegisterBody) -> dict:
    await rate_limit_request(request, "internal.discord_register", 30)
    existing = await get_db().users.find_one({"discord_id": payload.discordId})
    if existing:
        return {"exists": True, "username": existing["username"]}

    username = await _allocate_unique_username()
    password = generate_password()
    pass_key = generate_pass_key()
    referred_by_id = await _resolve_referrer_id(payload.refUsername)
    await get_db().users.insert_one(
        {
            "id": await next_id("users"),
            **_new_user_fields(
                username=username,
                password_hash=hash_password(password),
                pass_key_hash=hash_password(pass_key),
                telegram_id=None,
                discord_id=payload.discordId,
                referred_by_id=referred_by_id,
            ),
        }
    )
    return {
        "exists": False,
        "username": username,
        "password": password,
        "passKey": pass_key,
    }


# ── login (shared) ───────────────────────────────────────────────────────────

class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)
    provider: Literal["telegram", "discord"]
    telegramId: Optional[str] = Field(default=None, max_length=64)
    discordId: Optional[str] = Field(default=None, max_length=64)


def _provider_id_matches(row: dict, payload: LoginBody) -> bool:
    if payload.provider == "telegram":
        tid = (payload.telegramId or "").strip()
        return bool(tid and str(row.get("telegram_id") or "") == tid)
    did = (payload.discordId or "").strip()
    return bool(did and str(row.get("discord_id") or "") == did)


@router.post("/login")
async def internal_login(request: Request, payload: LoginBody) -> dict:
    await rate_limit_request(request, "internal.login", 20)
    from ..safe_url import normalize_username

    key = normalize_username(payload.username)
    if not key:
        return {"ok": False}
    await enforce_distributed_rate(f"user:{key}", "internal.login.user", 8)
    row = await get_db().users.find_one({"username": key})
    if row is None or row.get("banned"):
        return {"ok": False}
    if not verify_password(payload.password, row["password_hash"]):
        return {"ok": False}
    if not _provider_id_matches(row, payload):
        return {"ok": False}
    provider = payload.provider
    otp = await _issue_otp(row["id"], provider)
    return {
        "ok": True,
        "otpCode": otp,
        "provider": provider,
        "expiresInMinutes": int(OTP_TTL.total_seconds() // 60),
    }


class RecoverBody(BaseModel):
    passKey: str = Field(min_length=1, max_length=128)
    discordId: Optional[str] = Field(default=None, max_length=64)
    telegramId: Optional[str] = Field(default=None, max_length=64)


@router.post("/recover")
async def recover_credentials(request: Request, payload: RecoverBody) -> dict:
    """Verify recovery pass key for the linked Discord/Telegram account."""
    await rate_limit_request(request, "internal.recover", 10)
    db = get_db()
    if payload.discordId:
        await enforce_distributed_rate(
            f"discord:{payload.discordId.strip()}",
            "internal.recover.id",
            5,
        )
        user = await db.users.find_one({"discord_id": payload.discordId})
    elif payload.telegramId:
        await enforce_distributed_rate(
            f"telegram:{payload.telegramId.strip()}",
            "internal.recover.id",
            5,
        )
        user = await db.users.find_one({"telegram_id": payload.telegramId})
    else:
        return {"ok": False}
    if user is None or user.get("banned") or not user.get("pass_key_hash"):
        return {"ok": False}
    if not verify_password(payload.passKey.strip(), user["pass_key_hash"]):
        return {"ok": False}
    new_password = generate_password()
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": hash_password(new_password)}},
    )
    return {
        "ok": True,
        "username": user["username"],
        "password": new_password,
        "passKey": payload.passKey.strip(),
    }


# ── Bot lookups (deposit flows) ───────────────────────────────────────────────

class DiscordLookupBody(BaseModel):
    discordId: str = Field(min_length=1, max_length=64)


class TelegramLookupBody(BaseModel):
    telegramId: str = Field(min_length=1, max_length=64)


@router.post("/discord/lookup")
async def discord_lookup(payload: DiscordLookupBody) -> dict:
    user = await get_db().users.find_one({"discord_id": payload.discordId})
    if user is None:
        raise HTTPException(status_code=404, detail="not_registered")
    return {
        "ok": True,
        "userId": user["id"],
        "username": user["username"],
        "balancePln": float(user["balance_pln"]),
    }


@router.post("/telegram/lookup")
async def telegram_lookup(payload: TelegramLookupBody) -> dict:
    user = await get_db().users.find_one({"telegram_id": payload.telegramId})
    if user is None:
        raise HTTPException(status_code=404, detail="not_registered")
    return {
        "ok": True,
        "userId": user["id"],
        "username": user["username"],
        "balancePln": float(user["balance_pln"]),
    }


# ── Discord nick-reward ──────────────────────────────────────────────────────

class NickRewardBody(BaseModel):
    discordId: str = Field(min_length=1, max_length=64)


class TelegramNickRewardBody(BaseModel):
    telegramId: str = Field(min_length=1, max_length=64)


@router.post("/telegram/nick-reward")
async def telegram_nick_reward(payload: TelegramNickRewardBody) -> dict:
    user = await get_db().users.find_one({"telegram_id": payload.telegramId})
    if user is None:
        raise HTTPException(status_code=404, detail="not_registered")
    if user.get("last_nick_reward_at"):
        from datetime import datetime, timezone

        delta = datetime.now(timezone.utc) - user["last_nick_reward_at"]
        if delta < NICK_REWARD_COOLDOWN:
            ms_left = int((NICK_REWARD_COOLDOWN - delta).total_seconds() * 1000)
            raise HTTPException(
                status_code=429,
                detail={"error": "cooldown", "retryAfterMs": ms_left, "cooldownHours": 24},
            )
    doc = await create_redeem_code(
        NICK_REWARD_PLN,
        1,
        kind="nick",
        issued_to=user["id"],
        label="Nagroda za nick",
    )
    await get_db().users.update_one({"id": user["id"]}, {"$set": {"last_nick_reward_at": now()}})
    return {"ok": True, "code": doc["code"], "amountPln": float(NICK_REWARD_PLN)}


@router.post("/discord/nick-reward")
async def discord_nick_reward(payload: NickRewardBody) -> dict:
    user = await get_db().users.find_one({"discord_id": payload.discordId})
    if user is None:
        raise HTTPException(status_code=404, detail="not_registered")
    if user.get("last_nick_reward_at"):
        from datetime import datetime, timezone

        delta = datetime.now(timezone.utc) - user["last_nick_reward_at"]
        if delta < NICK_REWARD_COOLDOWN:
            ms_left = int((NICK_REWARD_COOLDOWN - delta).total_seconds() * 1000)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "cooldown",
                    "retryAfterMs": ms_left,
                    "cooldownHours": 24,
                },
            )

    doc = await create_redeem_code(
        NICK_REWARD_PLN,
        1,
        kind="nick",
        issued_to=user["id"],
        label="Nagroda za nick",
    )
    await get_db().users.update_one({"id": user["id"]}, {"$set": {"last_nick_reward_at": now()}})
    return {"ok": True, "code": doc["code"], "amountPln": float(NICK_REWARD_PLN)}


class DailyCodeBody(BaseModel):
    amountPln: Optional[Decimal] = None
    maxUses: Optional[int] = Field(default=None, ge=1, le=1_000_000)


@router.post("/codes/daily")
async def create_daily_code(payload: Optional[DailyCodeBody] = None) -> dict:
    """Create a new daily reward code (Discord midnight job / admin)."""
    from ..blik.settings_store import get_daily_code_config

    defaults = await get_daily_code_config()
    payload = payload or DailyCodeBody()
    amount = (
        payload.amountPln
        if payload.amountPln is not None
        else Decimal(str(defaults["amountPln"]))
    )
    max_uses = (
        payload.maxUses
        if payload.maxUses is not None
        else defaults["maxUses"]
    )
    doc = await create_redeem_code(
        amount,
        max_uses,
        kind="daily",
        label="Codzienna nagroda",
    )
    return {
        "ok": True,
        "code": doc["code"],
        "amountPln": float(amount),
        "maxUses": max_uses,
    }
