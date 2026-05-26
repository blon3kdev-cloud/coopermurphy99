"""BLIK public + internal API."""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import get_settings
from ..distributed_rate import enforce_distributed_rate
from ..rate_limit import get_remote_address, limiter, rate_limit_request
from ..session_cookies import get_blik_proof_token, set_blik_proof_cookie
from ..blik import (
    confirm_blik_sent,
    create_blik_withdraw,
    get_deposit_by_token,
    parse_pln,
    record_recipient_confirmation,
    start_blik_deposit,
    submit_manual_code,
    upload_proof,
)
from ..security import require_internal

public_router = APIRouter(prefix="/api/blik", tags=["blik-public"])
internal_router = APIRouter(prefix="/api/blik/internal", tags=["blik-internal"])


class StartDeposit(BaseModel):
    user_id: int
    amount_pln: str
    platform: Literal["discord", "telegram"]
    discord_id: Optional[str] = None
    telegram_id: Optional[str] = None


class ConfirmSent(BaseModel):
    deposit_id: int
    user_id: int


class RecipientConfirm(BaseModel):
    deposit_id: int
    user_id: int
    received: bool


class ManualCode(BaseModel):
    deposit_id: int
    user_id: int
    code: str = Field(min_length=6, max_length=16)


class CreateWithdraw(BaseModel):
    user_id: int
    amount_pln: str
    phone: str = Field(min_length=9, max_length=24)
    platform: Literal["discord", "telegram"]
    discord_id: Optional[str] = None
    telegram_id: Optional[str] = None


@internal_router.post("/deposit/start")
async def internal_start_deposit(
    payload: StartDeposit,
    _: None = Depends(require_internal),
) -> dict:
    amount = parse_pln(payload.amount_pln)
    return await start_blik_deposit(
        user_id=payload.user_id,
        amount_pln=amount,
        platform=payload.platform,
        discord_id=payload.discord_id,
        telegram_id=payload.telegram_id,
    )


@internal_router.post("/deposit/confirm-sent")
async def internal_confirm_sent(
    payload: ConfirmSent,
    _: None = Depends(require_internal),
) -> dict:
    return await confirm_blik_sent(payload.deposit_id, payload.user_id)


@internal_router.post("/deposit/recipient-confirm")
async def internal_recipient_confirm(
    payload: RecipientConfirm,
    _: None = Depends(require_internal),
) -> dict:
    return await record_recipient_confirmation(
        payload.deposit_id,
        payload.user_id,
        received=payload.received,
    )


@internal_router.post("/deposit/manual-code")
async def internal_manual_code(
    payload: ManualCode,
    _: None = Depends(require_internal),
) -> dict:
    return await submit_manual_code(payload.deposit_id, payload.user_id, payload.code)


@internal_router.post("/withdraw")
async def internal_create_withdraw(
    payload: CreateWithdraw,
    _: None = Depends(require_internal),
) -> dict:
    amount = parse_pln(payload.amount_pln)
    doc = await create_blik_withdraw(
        user_id=payload.user_id,
        amount_pln=amount,
        phone=payload.phone,
        platform=payload.platform,
        discord_id=payload.discord_id,
        telegram_id=payload.telegram_id,
    )
    return {
        "ok": True,
        "id": doc["id"],
        "amountPln": str(doc["amount_pln"]),
        "phone": doc["phone"],
        "status": doc["status"],
    }


class BlikExchange(BaseModel):
    token: str = Field(min_length=16, max_length=128)


@public_router.post("/confirm/exchange")
async def public_confirm_exchange(request: Request, payload: BlikExchange) -> JSONResponse:
    await rate_limit_request(request, "blik.confirm_exchange", 10)
    info = await get_deposit_by_token(payload.token.strip())
    response = JSONResponse(content=info)
    set_blik_proof_cookie(response, payload.token.strip())
    return response


@public_router.get("/confirm/session")
@limiter.limit("30/minute")
async def public_confirm_session(request: Request) -> dict:
    token = get_blik_proof_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="proof_required")
    return await get_deposit_by_token(token)


@public_router.post("/confirm/upload")
async def public_confirm_upload_cookie(
    request: Request,
    file: UploadFile = File(...),
) -> dict:
    await enforce_distributed_rate(
        get_remote_address(request), "blik_upload", 10, 60
    )
    token = get_blik_proof_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="proof_required")
    doc = await get_deposit_by_token(token)
    if not doc.get("canUpload"):
        raise HTTPException(status_code=400, detail="upload_not_allowed")
    return await upload_proof(token, file)


@public_router.get("/confirm/{token}")
@limiter.limit("30/minute")
async def public_confirm_info_legacy(request: Request, token: str) -> dict:
    """Legacy path-token URLs — disabled in production; use /confirm/exchange."""
    if not get_settings().is_development:
        raise HTTPException(status_code=404, detail="not_found")
    return await get_deposit_by_token(token)


@public_router.post("/confirm/{token}/upload")
async def public_confirm_upload_legacy(
    request: Request,
    token: str,
    file: UploadFile = File(...),
) -> dict:
    if not get_settings().is_development:
        raise HTTPException(status_code=404, detail="not_found")
    await enforce_distributed_rate(
        get_remote_address(request), "blik_upload", 10, 60
    )
    doc = await get_deposit_by_token(token)
    if not doc.get("canUpload"):
        raise HTTPException(status_code=400, detail="upload_not_allowed")
    return await upload_proof(token, file)
