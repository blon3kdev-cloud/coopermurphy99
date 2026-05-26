"""Wallet — balance + deposit/withdraw stubs (records request rows)."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..db import get_db, next_id, now
from ..distributed_rate import enforce_distributed_rate
from ..playthrough_service import ensure_withdraw_allowed
from ..rate_limit import get_remote_address
from ..security import get_current_user
from ..wallet_service import hold_withdraw_balance

router = APIRouter(prefix="/api/wallet", tags=["wallet"])


def _fmt(amount: Decimal) -> str:
    return f"{float(amount):,.2f}".replace(",", "\u00a0").replace(".", ",")


@router.get("/balance")
async def get_balance(user: dict = Depends(get_current_user)) -> dict:
    return {"balance": _fmt(user["balance_pln"]), "balanceRaw": float(user["balance_pln"]), "currency": "PLN"}


class WalletOp(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=2)


@router.post("/deposit")
async def request_deposit(
    request: Request, payload: WalletOp, user: dict = Depends(get_current_user)
) -> dict:
    await enforce_distributed_rate(
        get_remote_address(request), "wallet.deposit", 20
    )
    op_id = await next_id("wallet_ops")
    await get_db().wallet_ops.insert_one(
        {
            "id": op_id,
            "user_id": user["id"],
            "kind": "deposit",
            "amount_pln": payload.amount,
            "status": "pending",
            "created_at": now(),
        }
    )
    return {"ok": True, "id": op_id}


@router.post("/withdraw")
async def request_withdraw(
    request: Request, payload: WalletOp, user: dict = Depends(get_current_user)
) -> dict:
    await enforce_distributed_rate(
        get_remote_address(request), "wallet.withdraw", 20
    )
    await ensure_withdraw_allowed(user["id"])
    await hold_withdraw_balance(user["id"], payload.amount)
    op_id = await next_id("wallet_ops")
    await get_db().wallet_ops.insert_one(
        {
            "id": op_id,
            "user_id": user["id"],
            "kind": "withdraw",
            "amount_pln": payload.amount,
            "held_pln": payload.amount,
            "status": "pending",
            "created_at": now(),
        }
    )
    return {"ok": True, "id": op_id}
