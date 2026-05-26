"""Internal crypto payment endpoints (bots / automation)."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..api_errors import http_400_from_value_error
from ..payments import PaymentService, verify_master_addresses
from ..payments.types import PaymentAsset, PaymentKind, parse_amount, require_asset_enabled
from ..rate_limit import limiter, rate_limit_request
from ..security import require_internal

router = APIRouter(prefix="/api/payments/internal", tags=["payments-internal"])


class CreateDeposit(BaseModel):
    asset: str
    amount: str
    user_id: Optional[int] = None
    amount_pln: Optional[str] = None


class CreateWithdraw(BaseModel):
    asset: str
    amount: str
    destination_address: str
    user_id: Optional[int] = None
    amount_pln: Optional[str] = None


def _asset(raw: str) -> PaymentAsset:
    try:
        return PaymentAsset(raw.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid_asset") from None


@router.post("/deposit")
async def create_deposit(
    request: Request,
    payload: CreateDeposit,
    _: None = Depends(require_internal),
) -> dict:
    await rate_limit_request(request, "payments.deposit", 30)
    verify_master_addresses()
    asset = _asset(payload.asset)
    try:
        require_asset_enabled(asset)
        amount = parse_amount(asset, payload.amount)
    except ValueError as e:
        raise http_400_from_value_error(e) from e
    amount_pln = None
    if payload.amount_pln:
        try:
            amount_pln = Decimal(payload.amount_pln.strip())
        except Exception:
            raise HTTPException(status_code=400, detail="invalid_amount_pln") from None
    doc = await PaymentService.create_deposit(
        asset, amount, payload.user_id, amount_pln=amount_pln
    )
    return {
        "ok": True,
        "id": doc["id"],
        "address": doc["address"],
        "asset": doc["asset"],
        "amount": str(doc["amount_expected"]),
        "amountPln": str(doc["amount_pln"]) if doc.get("amount_pln") is not None else None,
        "matchedWithdraw": doc.get("matched_withdraw_id"),
        "fundsWithdrawal": bool(doc.get("funds_user_address")),
        "expiresAt": doc["expires_at"].isoformat(),
    }


@router.post("/withdraw")
async def create_withdraw(
    request: Request,
    payload: CreateWithdraw,
    _: None = Depends(require_internal),
) -> dict:
    await rate_limit_request(request, "payments.withdraw", 30)
    asset = _asset(payload.asset)
    try:
        require_asset_enabled(asset)
        amount = parse_amount(asset, payload.amount)
    except ValueError as e:
        raise http_400_from_value_error(e) from e
    amount_pln = None
    if payload.amount_pln:
        try:
            amount_pln = Decimal(payload.amount_pln.strip())
        except Exception:
            raise HTTPException(status_code=400, detail="invalid_amount_pln") from None
    if payload.user_id is not None:
        from ..playthrough_service import ensure_withdraw_allowed

        await ensure_withdraw_allowed(payload.user_id)
    try:
        doc = await PaymentService.create_withdraw(
            asset,
            amount,
            payload.destination_address,
            payload.user_id,
            amount_pln=amount_pln,
        )
    except ValueError as e:
        raise http_400_from_value_error(e) from e
    return {"ok": True, "id": doc["id"], "status": doc["status"]}


@router.get("/{payment_id}")
@limiter.limit("30/minute")
async def get_payment(
    request: Request,
    payment_id: int,
    _: None = Depends(require_internal),
) -> dict:
    doc = await PaymentService.get_payment(payment_id)
    if not doc:
        raise HTTPException(status_code=404, detail="not found")
    out = {k: v for k, v in doc.items() if k != "_id"}
    for key in ("created_at", "expires_at", "confirmed_at"):
        if out.get(key):
            out[key] = out[key].isoformat()
    if out.get("amount_expected") is not None:
        out["amount_expected"] = str(out["amount_expected"])
    if out.get("amount_received") is not None:
        out["amount_received"] = str(out["amount_received"])
    return out
