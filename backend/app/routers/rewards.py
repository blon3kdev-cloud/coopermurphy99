"""VIP + referral panels. Redeem-code claim consumes a `redeem_codes` row."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..distributed_rate import enforce_distributed_rate
from ..rate_limit import get_remote_address, rate_limit_request
from ..redeem_lockout import assert_redeem_not_locked
from ..rewards_service import (
    attach_referrer,
    build_referral_payload,
    build_vip_payload,
    claim_referral_tier,
    claim_vip_bonus,
    redeem_code,
)
from ..security import get_current_user

router = APIRouter(prefix="/api/rewards", tags=["rewards"])


@router.get("/vip")
async def get_vip(user: dict = Depends(get_current_user)) -> dict:
    return await build_vip_payload(user)


class Claim(BaseModel):
    kind: str = Field(min_length=1, max_length=32)


@router.post("/vip/claim")
async def claim_bonus(
    request: Request,
    payload: Claim,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "rewards.vip_claim", 20)
    return await claim_vip_bonus(user, payload.kind)


@router.get("/referral")
async def get_referral(user: dict = Depends(get_current_user)) -> dict:
    return await build_referral_payload(user)


class ReferralClaim(BaseModel):
    tier: int = Field(ge=1, le=32)


@router.post("/referral/claim")
async def claim_referral(
    request: Request,
    payload: ReferralClaim,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "rewards.referral_claim", 20)
    return await claim_referral_tier(user, payload.tier)


class AttachReferral(BaseModel):
    ref: str = Field(min_length=1, max_length=64)


@router.post("/referral/attach")
async def attach_referral(
    request: Request,
    payload: AttachReferral,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "rewards.referral_attach", 20)
    return await attach_referrer(user, payload.ref)


class Redeem(BaseModel):
    code: str = Field(min_length=8, max_length=64)


@router.post("/redeem")
async def redeem(
    request: Request,
    payload: Redeem,
    user: dict = Depends(get_current_user),
) -> dict:
    client_key = get_remote_address(request)
    await rate_limit_request(request, "rewards.redeem", 6)
    await enforce_distributed_rate(client_key, "rewards.redeem.ip", 6)
    await enforce_distributed_rate(
        str(user["id"]), "rewards.redeem.user", 6
    )
    await assert_redeem_not_locked(user["id"], client_key)
    return await redeem_code(user, payload.code, client_key=client_key)
