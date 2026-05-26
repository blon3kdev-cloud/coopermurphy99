"""Match deposits to pending withdrawals — pay user withdrawal addresses on-chain."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional

import httpx

from ..db import get_db, now
from .monitors.registry import check_payment_delta, get_address_holdings
from .types import PaymentAsset, PaymentKind, PaymentStatus

log = logging.getLogger(__name__)


def withdraw_remaining(doc: dict[str, Any]) -> Decimal:
    expected = Decimal(str(doc["amount_expected"]))
    filled = Decimal(str(doc.get("amount_filled") or 0))
    return max(expected - filled, Decimal(0))


async def find_open_withdraw(asset: PaymentAsset) -> Optional[dict[str, Any]]:
    """Oldest pending withdrawal with remaining amount for this asset."""
    cursor = (
        get_db()
        .crypto_payments.find(
            {
                "kind": PaymentKind.WITHDRAW.value,
                "asset": asset.value,
                "status": PaymentStatus.PENDING.value,
            }
        )
        .sort("created_at", 1)
    )
    async for doc in cursor:
        if withdraw_remaining(doc) > 0:
            return doc
    return None


async def try_match_deposit(
    asset: PaymentAsset,
    amount: Decimal,
    *,
    amount_pln: Optional[Decimal] = None,
) -> Optional[dict[str, Any]]:
    """
    If a pending withdrawal exists, route the deposit to its destination address.
    Deposit amount is capped to the withdrawal's remaining need.
    """
    withdraw = await find_open_withdraw(asset)
    if not withdraw:
        return None

    dest = (withdraw.get("destination_address") or "").strip()
    if not dest:
        return None

    remaining = withdraw_remaining(withdraw)
    pay_amount = min(amount, remaining)
    if pay_amount <= 0:
        return None

    pln = amount_pln
    if pln is not None and amount > 0 and pay_amount < amount:
        pln = (pln * pay_amount / amount).quantize(Decimal("0.01"))

    baseline = await _snapshot_baseline(asset, dest)

    return {
        "address": dest,
        "amount_expected": pay_amount,
        "amount_pln": pln,
        "matched_withdraw_id": withdraw["id"],
        "address_balance_baseline": baseline,
        "funds_user_address": True,
    }


async def _snapshot_baseline(asset: PaymentAsset, address: str) -> str:
    async with httpx.AsyncClient() as client:
        holdings = await get_address_holdings(client, asset, address)
    return str(holdings)


async def on_deposit_confirmed(doc: dict[str, Any]) -> None:
    """Apply confirmed deposit to linked withdrawal and credit depositor balance."""
    wid = doc.get("matched_withdraw_id")
    received = Decimal(str(doc.get("amount_received") or doc["amount_expected"]))

    if wid:
        db = get_db()
        withdraw = await db.crypto_payments.find_one({"id": wid})
        if withdraw and withdraw["status"] == PaymentStatus.PENDING.value:
            new_filled = Decimal(str(withdraw.get("amount_filled") or 0)) + received
            patch: dict[str, Any] = {
                "amount_filled": new_filled,
                "updated_at": now(),
            }
            if new_filled >= Decimal(str(withdraw["amount_expected"])):
                patch["status"] = PaymentStatus.CONFIRMED.value
                patch["confirmed_at"] = now()
            await db.crypto_payments.update_one({"id": wid}, {"$set": patch})
            log.info(
                "withdraw %s filled %s / %s",
                wid,
                new_filled,
                withdraw["amount_expected"],
            )

    user_id = doc.get("user_id")
    pln = doc.get("amount_pln")
    if user_id and pln is not None:
        pln_val = Decimal(str(pln))
        if pln_val > 0:
            await get_db().users.update_one(
                {"id": user_id},
                {"$inc": {"balance_pln": pln_val, "playthrough_base_pln": pln_val}},
            )


async def check_matched_deposit(
    client: httpx.AsyncClient,
    doc: dict[str, Any],
) -> Optional[Any]:
    """Poll on-chain delta for deposits sent to a withdrawal destination address."""
    from .monitors.base import MonitorResult

    asset = PaymentAsset(doc["asset"])
    address = doc["address"]
    expected = Decimal(str(doc["amount_expected"]))
    baseline = Decimal(str(doc.get("address_balance_baseline") or 0))
    return await check_payment_delta(client, asset, address, baseline, expected)
