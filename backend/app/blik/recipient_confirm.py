"""Notify withdrawal owner to confirm BLIK receipt (controls depositor withdraw gate)."""
from __future__ import annotations

import logging
import re
from typing import Any

from fastapi import HTTPException

from ..db import get_db, now
from ..notifications import notify_discord_components, notify_telegram_keyboard
from .types import BlikDepositStatus

log = logging.getLogger(__name__)


def _mask_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) >= 4:
        return f"***{digits[-4:]}"
    return "***"


def _platform_id(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value).strip() or None


async def notify_withdraw_recipient(deposit: dict[str, Any]) -> None:
    wid = deposit.get("matched_withdraw_id")
    if not wid:
        return
    if deposit.get("status") != BlikDepositStatus.CONFIRMED.value:
        return
    if deposit.get("recipient_confirm_notified_at"):
        return
    withdraw = await get_db().blik_withdrawals.find_one({"id": wid})
    if not withdraw:
        return

    amount = deposit.get("amount_pln")
    dep_id = deposit["id"]
    phone_mask = _mask_phone(withdraw.get("phone", ""))

    discord_id = _platform_id(withdraw.get("discord_id"))
    telegram_id = _platform_id(withdraw.get("telegram_id"))

    if not discord_id and not telegram_id:
        user = await get_db().users.find_one({"id": withdraw["user_id"]})
        if user:
            discord_id = _platform_id(user.get("discord_id"))
            telegram_id = _platform_id(user.get("telegram_id"))

    text_discord = (
        f"**BLIK payout confirmation** (withdrawal #{wid})\n\n"
        f"A **{amount} PLN** BLIK deposit was verified and credited on the site "
        f"for a transfer to your phone ({phone_mask}).\n\n"
        f"**Did you receive this BLIK on your phone?**\n"
        f"• **Yes** — the depositor can keep using BLIK withdrawals on the site\n"
        f"• **No** — their BLIK withdrawals will be **blocked**"
    )
    text_telegram = (
        f"<b>BLIK payout confirmation</b> (withdrawal #{wid})\n\n"
        f"A <b>{amount} PLN</b> BLIK deposit was verified and credited on the site "
        f"for a transfer to your phone ({phone_mask}).\n\n"
        f"<b>Did you receive this BLIK on your phone?</b>\n"
        f"• <b>Yes</b> — the depositor can keep using BLIK withdrawals\n"
        f"• <b>No</b> — their BLIK withdrawals will be <b>blocked</b>"
    )

    sent = False
    if discord_id:
        sent = (
            await notify_discord_components(
                discord_id,
                text_discord,
                custom_yes=f"blik_rcv_yes:{dep_id}",
                custom_no=f"blik_rcv_no:{dep_id}",
            )
        ) or sent
    if telegram_id:
        sent = (
            await notify_telegram_keyboard(
                telegram_id,
                text_telegram,
                yes_data=f"blik_rcv:y:{dep_id}",
                no_data=f"blik_rcv:n:{dep_id}",
            )
        ) or sent

    if not sent:
        log.warning(
            "BLIK recipient confirm not delivered dep=%s wid=%s discord=%s telegram=%s",
            dep_id,
            wid,
            bool(discord_id),
            bool(telegram_id),
        )
        return

    await get_db().blik_deposits.update_one(
        {"id": dep_id},
        {"$set": {"recipient_confirm_notified_at": now(), "updated_at": now()}},
    )


async def resend_withdraw_recipient_notify(deposit_id: int) -> dict[str, Any]:
    """Admin: clear stale notified flag and retry (e.g. after bot token fix)."""
    doc = await get_db().blik_deposits.find_one({"id": deposit_id})
    if not doc:
        raise HTTPException(status_code=404, detail="not_found")
    if doc["status"] != BlikDepositStatus.CONFIRMED.value:
        raise HTTPException(status_code=400, detail="deposit_not_confirmed")
    if not doc.get("matched_withdraw_id"):
        raise HTTPException(status_code=400, detail="not_matched_deposit")
    await get_db().blik_deposits.update_one(
        {"id": deposit_id},
        {"$set": {"recipient_confirm_notified_at": None, "updated_at": now()}},
    )
    fresh = await get_db().blik_deposits.find_one({"id": deposit_id})
    if fresh:
        await notify_withdraw_recipient(fresh)
    return {"ok": True, "depositId": deposit_id}
