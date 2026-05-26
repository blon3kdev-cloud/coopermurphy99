"""Shared BLIK deposit/withdraw helpers for Discord and Telegram bots."""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from app.blik.code_utils import normalize_blik_code

from bots.shared import BackendError, call_backend, format_withdraw_detail

log = logging.getLogger("bots.blik")

BLIK_CODE_HINT = "The code must be exactly 6 digits — e.g. 123456 or 123 456."


def parse_pln(text: str) -> Decimal:
    pln = Decimal(str(text).strip().replace(",", "."))
    if pln <= 0:
        raise ValueError("Amount must be greater than zero")
    return pln


async def blik_start_deposit(
    *,
    user_id: int,
    amount_pln: Decimal,
    platform: str,
    discord_id: str | None = None,
    telegram_id: str | None = None,
) -> dict:
    return await call_backend(
        "/api/blik/internal/deposit/start",
        {
            "user_id": user_id,
            "amount_pln": str(amount_pln),
            "platform": platform,
            "discord_id": discord_id,
            "telegram_id": telegram_id,
        },
    )


async def blik_confirm_sent(deposit_id: int, user_id: int) -> dict:
    return await call_backend(
        "/api/blik/internal/deposit/confirm-sent",
        {"deposit_id": deposit_id, "user_id": user_id},
    )


async def blik_recipient_confirm(deposit_id: int, user_id: int, *, received: bool) -> dict:
    return await call_backend(
        "/api/blik/internal/deposit/recipient-confirm",
        {
            "deposit_id": deposit_id,
            "user_id": user_id,
            "received": received,
        },
    )


async def blik_submit_code(deposit_id: int, user_id: int, code: str) -> dict:
    normalized = normalize_blik_code(code)
    if not normalized:
        raise ValueError(BLIK_CODE_HINT)
    return await call_backend(
        "/api/blik/internal/deposit/manual-code",
        {"deposit_id": deposit_id, "user_id": user_id, "code": normalized},
    )


def blik_code_error_message(exc: BackendError) -> str:
    detail = exc.data.get("detail")
    if detail == "invalid_blik_code":
        return f"❌ {BLIK_CODE_HINT}"
    if detail == "invalid_flow":
        return "❌ This deposit does not use a BLIK code. Start **Deposit** again and choose the code flow."
    if detail == "invalid_status":
        return "❌ This deposit has expired or the code was already submitted."
    if detail == "expired":
        return "❌ This deposit has expired. Start **Deposit** again."
    if isinstance(detail, str):
        return f"❌ {detail}"
    if isinstance(detail, list):
        return f"❌ {BLIK_CODE_HINT}"
    return f"❌ {BLIK_CODE_HINT}"


async def blik_create_withdraw(
    *,
    user_id: int,
    amount_pln: Decimal,
    phone: str,
    platform: str,
    discord_id: str | None = None,
    telegram_id: str | None = None,
) -> dict:
    return await call_backend(
        "/api/blik/internal/withdraw",
        {
            "user_id": user_id,
            "amount_pln": str(amount_pln),
            "phone": phone,
            "platform": platform,
            "discord_id": discord_id,
            "telegram_id": telegram_id,
        },
    )


def withdraw_error_message(exc: BackendError) -> str:
    detail = exc.data.get("detail")
    msg = format_withdraw_detail(detail)
    if msg:
        return msg
    if detail in ("blik_withdraw_pending_recipient", "blik_withdraw_blocked"):
        return "❌ **BLIK withdrawal is unavailable right now.** Contact support if you need help."
    if isinstance(detail, str):
        return f"❌ {detail}"
    return "❌ Withdrawal failed."


def deposit_error_message(exc: BackendError) -> str:
    detail = exc.data.get("detail")
    if detail == "no_matching_withdrawal":
        return "❌ **BLIK is currently unavailable.**"
    if isinstance(detail, str):
        return f"❌ {detail}"
    return "❌ BLIK deposit could not be started. Try again or contact support."
