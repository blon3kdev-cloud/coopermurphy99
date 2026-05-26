"""Customer-facing auth: OTP verify (issued by bots), session, logout."""

import hashlib
import hmac
from typing import Literal, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import get_settings
from ..db import get_db, next_id, now
from ..distributed_rate import enforce_distributed_rate
from ..otp_lockout import assert_otp_not_locked, clear_otp_failures, record_otp_failure
from ..rate_limit import get_remote_address, limiter
from ..session_cookies import (
    clear_user_session_cookies,
    get_user_token_from_request,
    set_user_session_cookie,
)
from ..security import (
    SESSION_TTL,
    generate_token,
    hash_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class VerifyOtpBody(BaseModel):
    provider: Literal["telegram", "discord"]
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class DevLoginBody(BaseModel):
    code: str = Field(min_length=1, max_length=64)


def _format_balance(balance) -> str:
    return f"{float(balance):,.2f}".replace(",", "\u00a0").replace(".", ",")


def _otp_lookup_key(provider: str, code: str) -> str:
    return hashlib.sha256(f"{provider}:{code}".encode("utf-8")).hexdigest()


@router.post("/verify-otp")
@limiter.limit("5/minute")
async def verify_otp(request: Request, payload: VerifyOtpBody = Body()) -> dict:
    """Single-use 6-digit code → bearer token + minimal session."""
    client_key = get_remote_address(request)
    await enforce_distributed_rate(client_key, "auth.verify_otp", 5)
    await assert_otp_not_locked(payload.provider, client_key)

    db = get_db()
    lookup_key = _otp_lookup_key(payload.provider, payload.code)
    otp = await db.otp_codes.find_one(
        {
            "provider": payload.provider,
            "lookup_key": lookup_key,
            "used_at": None,
            "expires_at": {"$gt": now()},
        }
    )
    matched = None
    user = None
    if otp and verify_password(payload.code, otp["code_hash"]):
        matched = otp
        user = await db.users.find_one({"id": otp["user_id"]})
    if matched is None or user is None or user.get("banned"):
        await record_otp_failure(payload.provider, client_key)
        raise HTTPException(status_code=401, detail="invalid_code")

    await clear_otp_failures(payload.provider, client_key)
    token, token_hash = generate_token()
    await db.otp_codes.update_one({"id": matched["id"]}, {"$set": {"used_at": now()}})
    await db.sessions.insert_one(
        {
            "id": await next_id("sessions"),
            "user_id": matched["user_id"],
            "token_hash": token_hash,
            "created_at": now(),
            "expires_at": now() + SESSION_TTL,
        }
    )

    body = {
        "ok": True,
        "username": user["username"],
        "balance": _format_balance(user["balance_pln"]),
    }
    response = JSONResponse(content=body)
    set_user_session_cookie(response, token, SESSION_TTL)
    return response


@router.post("/logout")
async def logout(request: Request) -> JSONResponse:
    token = get_user_token_from_request(request)
    if token:
        await get_db().sessions.delete_one({"token_hash": hash_token(token)})
    response = JSONResponse(content={"ok": True})
    clear_user_session_cookies(response)
    return response


@router.get("/session")
async def get_session(request: Request) -> Optional[dict]:
    token = get_user_token_from_request(request)
    if not token:
        return None
    db = get_db()
    session = await db.sessions.find_one(
        {"token_hash": hash_token(token), "expires_at": {"$gt": now()}}
    )
    if session is None:
        return None
    user = await db.users.find_one({"id": session["user_id"]})
    if user is None:
        return None
    return {"username": user["username"], "balance": _format_balance(user["balance_pln"])}


@router.post("/register")
async def register(request: Request) -> dict:
    """Stub — real registration happens via Telegram/Discord bots."""
    if not get_settings().is_development:
        raise HTTPException(status_code=404, detail="not_found")
    from ..mongo_sanitize import reject_operators

    body = await request.json()
    reject_operators(body)
    return {"ok": True}


@router.get("/dev-enabled")
async def dev_enabled() -> dict:
    """Whether dev login is available (development + DEV_LOGIN_CODE set)."""
    return {"enabled": get_settings().dev_login_enabled}


@router.post("/dev-login")
@limiter.limit("20/minute")
async def dev_login(request: Request, payload: DevLoginBody = Body()) -> dict:
    """Development-only login for the seeded test user (no bot OTP)."""
    settings = get_settings()
    if not settings.dev_login_enabled:
        raise HTTPException(status_code=404, detail="not available")

    expected = settings.dev_login_code.strip()
    if not hmac.compare_digest(payload.code.strip(), expected):
        raise HTTPException(status_code=401, detail="invalid code")

    row = await get_db().users.find_one({"username": settings.dev_username})
    if row is None or row.get("banned"):
        raise HTTPException(status_code=503, detail="dev user missing — restart backend")

    token, token_hash = generate_token()
    await get_db().sessions.insert_one(
        {
            "id": await next_id("sessions"),
            "user_id": row["id"],
            "token_hash": token_hash,
            "created_at": now(),
            "expires_at": now() + SESSION_TTL,
        }
    )
    body = {
        "ok": True,
        "username": row["username"],
        "balance": _format_balance(row["balance_pln"]),
    }
    response = JSONResponse(content=body)
    set_user_session_cookie(response, token, SESSION_TTL)
    return response
