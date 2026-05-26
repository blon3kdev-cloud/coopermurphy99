"""Crash — shared real-time multiplier rounds."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket
from pydantic import BaseModel, Field

from ..api_errors import http_400_from_value_error
from ..crash_engine import get_crash_engine
from ..db import get_db
from ..rate_limit import rate_limit_request
from ..routers.games import _lock_stake
from ..security import get_current_user, get_optional_user_id

router = APIRouter(prefix="/api/games/crash", tags=["games"])


class CrashBetBody(BaseModel):
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    autoCashout: Optional[float] = Field(default=None, ge=1.01, le=1_000_000)


@router.get("/state")
async def crash_state(user_id: int | None = Depends(get_optional_user_id)) -> dict:
    engine = get_crash_engine()
    snap = engine.public_snapshot(user_id)
    if user_id is not None:
        db = get_db()
        doc = await db.users.find_one({"id": user_id})
        snap["balance"] = float(doc["balance_pln"]) if doc else 0.0
    return {"ok": True, **snap}


@router.post("/bet")
async def crash_bet(
    request: Request,
    payload: CrashBetBody,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.crash", 30)
    engine = get_crash_engine()
    stake = payload.stakePln

    async def lock() -> None:
        await _lock_stake(user["id"], stake)

    try:
        snap = await engine.place_bet(
            user["id"],
            stake,
            payload.autoCashout,
            lock,
        )
    except ValueError as exc:
        raise http_400_from_value_error(exc) from exc

    db = get_db()
    doc = await db.users.find_one({"id": user["id"]})
    snap["balance"] = float(doc["balance_pln"]) if doc else 0.0
    return {"ok": True, **snap}


@router.post("/cashout")
async def crash_cashout(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.crash", 60)
    engine = get_crash_engine()
    try:
        snap = await engine.cashout(user["id"])
    except ValueError as exc:
        raise http_400_from_value_error(exc) from exc
    return {"ok": True,  **snap}


@router.post("/cancel")
async def crash_cancel(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.crash", 30)
    engine = get_crash_engine()
    try:
        snap = await engine.cancel_bet(user["id"])
    except ValueError as exc:
        raise http_400_from_value_error(exc) from exc
    return {"ok": True, **snap}


@router.websocket("/ws")
async def crash_ws(websocket: WebSocket) -> None:
    user_id = await get_optional_user_id(websocket)
    client_ip = websocket.client.host if websocket.client else "unknown"
    await get_crash_engine().connect(websocket, user_id, client_ip=client_ip)
