"""BLIK deposit / withdrawal business logic."""
from __future__ import annotations

import logging
import re
import secrets
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, UploadFile

from ..config import get_settings
from ..db import as_utc, get_db, next_id, now
from ..notifications import notify_deposit_event
from ..playthrough_service import ensure_withdraw_allowed
from .recipient_confirm import notify_withdraw_recipient
from .settings_store import get_admin_flags
from .types import BlikDepositFlow, BlikDepositStatus, BlikWithdrawStatus
from .code_utils import format_blik_code, normalize_blik_code
from .verify import verify_blik_proof

log = logging.getLogger(__name__)

DEPOSIT_TTL_MIN = 90
MAX_PROOF_ATTEMPTS = 3

_CONTENT_TYPE_KIND = {
    "image/jpeg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
    "application/pdf": "application/pdf",
}


def _sniff_file_kind(data: bytes) -> str | None:
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"%PDF":
        return "application/pdf"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _upload_dir() -> Path:
    base = Path(get_settings().blik_upload_dir)
    base.mkdir(parents=True, exist_ok=True)
    try:
        base.chmod(0o700)
    except OSError:
        pass
    return base


def _confirm_url(token: str) -> str:
    origin = get_settings().frontend_origin.split(",")[0].strip().rstrip("/")
    return f"{origin}/blik/confirm#{token}"


async def _release_stale_matches() -> None:
    """If a matched deposit expired/failed, reopen the withdrawal for matching."""
    db = get_db()
    cursor = db.blik_withdrawals.find({"status": BlikWithdrawStatus.MATCHED.value})
    async for w in cursor:
        dep_id = w.get("matched_deposit_id")
        if not dep_id:
            continue
        dep = await db.blik_deposits.find_one({"id": dep_id})
        if not dep:
            continue
        if dep["status"] == BlikDepositStatus.CONFIRMED.value:
            continue
        expired = dep["status"] in (
            BlikDepositStatus.EXPIRED.value,
            BlikDepositStatus.FAILED.value,
        ) or now() > as_utc(dep.get("expires_at") or now())
        if not expired:
            continue
        if dep["status"] not in (
            BlikDepositStatus.EXPIRED.value,
            BlikDepositStatus.FAILED.value,
        ):
            await db.blik_deposits.update_one(
                {"id": dep_id},
                {"$set": {"status": BlikDepositStatus.EXPIRED.value, "updated_at": now()}},
            )
        await db.blik_withdrawals.update_one(
            {"id": w["id"]},
            {
                "$set": {
                    "status": BlikWithdrawStatus.PENDING.value,
                    "matched_deposit_id": None,
                    "updated_at": now(),
                }
            },
        )


async def find_matching_withdraw(amount_pln: Decimal) -> Optional[dict[str, Any]]:
    """Oldest pending BLIK withdrawal with exact PLN amount."""
    await _release_stale_matches()
    cursor = (
        get_db()
        .blik_withdrawals.find(
            {
                "status": BlikWithdrawStatus.PENDING.value,
                "amount_pln": amount_pln,
            }
        )
        .sort("created_at", 1)
    )
    async for doc in cursor:
        return doc
    return None


async def _set_blik_withdraw_blocked(user_id: int, blocked: bool) -> None:
    await get_db().users.update_one(
        {"id": user_id},
        {"$set": {"blik_withdraw_blocked": blocked, "updated_at": now()}},
    )


async def _depositor_blik_withdraw_block_reason(user_id: int) -> str | None:
    """Why this user cannot start a BLIK withdrawal (None = allowed)."""
    user = await get_db().users.find_one({"id": user_id})
    if not user:
        return None
    if user.get("blik_withdraw_blocked"):
        return "blik_withdraw_blocked"
    pending = await get_db().blik_deposits.find_one(
        {
            "user_id": user_id,
            "status": BlikDepositStatus.CONFIRMED.value,
            "matched_withdraw_id": {"$ne": None},
            "recipient_confirmed": None,
        }
    )
    if pending:
        return "blik_withdraw_pending_recipient"
    return None


async def create_blik_withdraw(
    *,
    user_id: int,
    amount_pln: Decimal,
    phone: str,
    platform: str,
    discord_id: str | None = None,
    telegram_id: str | None = None,
) -> dict[str, Any]:
    phone = phone.strip()
    if len(re.sub(r"\D", "", phone)) < 9:
        raise HTTPException(status_code=400, detail="invalid_phone")

    block_reason = await _depositor_blik_withdraw_block_reason(user_id)
    if block_reason:
        raise HTTPException(status_code=403, detail=block_reason)

    await ensure_withdraw_allowed(user_id)

    db = get_db()
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    if user["balance_pln"] < amount_pln:
        raise HTTPException(status_code=400, detail="insufficient balance")
    updated = await db.users.find_one_and_update(
        {"id": user_id, "balance_pln": {"$gte": amount_pln}},
        {"$inc": {"balance_pln": -amount_pln}},
    )
    if not updated:
        raise HTTPException(status_code=400, detail="insufficient balance")

    wid = await next_id("blik_withdrawals")
    doc = {
        "id": wid,
        "user_id": user_id,
        "amount_pln": amount_pln,
        "phone": phone,
        "platform": platform,
        "discord_id": discord_id,
        "telegram_id": telegram_id,
        "status": BlikWithdrawStatus.PENDING.value,
        "matched_deposit_id": None,
        "created_at": now(),
        "updated_at": now(),
    }
    await get_db().blik_withdrawals.insert_one(doc)
    return doc


async def start_blik_deposit(
    *,
    user_id: int,
    amount_pln: Decimal,
    platform: str,
    discord_id: str | None = None,
    telegram_id: str | None = None,
) -> dict[str, Any]:
    await _release_stale_matches()
    flags = await get_admin_flags()
    withdraw = await find_matching_withdraw(amount_pln)

    if withdraw:
        flow = BlikDepositFlow.MATCHED
        status = BlikDepositStatus.PENDING_SEND
        matched_withdraw_id = withdraw["id"]
        withdraw_phone = withdraw["phone"]
    elif flags["blikActive"]:
        flow = BlikDepositFlow.MANUAL_CODE
        status = BlikDepositStatus.MANUAL_PENDING
        matched_withdraw_id = None
        withdraw_phone = None
    else:
        raise HTTPException(
            status_code=400,
            detail="no_matching_withdrawal",
        )

    token = secrets.token_urlsafe(32)
    dep_id = await next_id("blik_deposits")
    expires = now() + timedelta(minutes=DEPOSIT_TTL_MIN)
    doc = {
        "id": dep_id,
        "user_id": user_id,
        "amount_pln": amount_pln,
        "flow": flow.value,
        "status": status.value,
        "platform": platform,
        "discord_id": discord_id,
        "telegram_id": telegram_id,
        "matched_withdraw_id": matched_withdraw_id,
        "withdraw_phone": withdraw_phone,
        "upload_token": token,
        "proof_attempts": 0,
        "manual_code": None,
        "proof_path": None,
        "proof_verification": None,
        "recipient_confirmed": None,
        "recipient_confirmed_at": None,
        "recipient_confirm_notified_at": None,
        "admin_note": None,
        "created_at": now(),
        "updated_at": now(),
        "expires_at": expires,
        "confirmed_at": None,
    }
    await get_db().blik_deposits.insert_one(doc)

    if withdraw:
        await get_db().blik_withdrawals.update_one(
            {"id": withdraw["id"]},
            {
                "$set": {
                    "status": BlikWithdrawStatus.MATCHED.value,
                    "matched_deposit_id": dep_id,
                    "updated_at": now(),
                }
            },
        )

    out: dict[str, Any] = {
        "id": dep_id,
        "flow": flow.value,
        "status": status.value,
        "amountPln": str(amount_pln),
        "expiresAt": expires.isoformat(),
    }
    if flow == BlikDepositFlow.MATCHED:
        out["withdrawPhone"] = withdraw_phone
        out["withdrawAmountPln"] = str(amount_pln)
        out["matchedWithdrawId"] = matched_withdraw_id
    return out


async def confirm_blik_sent(deposit_id: int, user_id: int) -> dict[str, Any]:
    doc = await _get_deposit_for_user(deposit_id, user_id)
    if doc["flow"] != BlikDepositFlow.MATCHED.value:
        raise HTTPException(status_code=400, detail="invalid_flow")
    if doc["status"] != BlikDepositStatus.PENDING_SEND.value:
        raise HTTPException(status_code=400, detail="invalid_status")

    await get_db().blik_deposits.update_one(
        {"id": deposit_id},
        {
            "$set": {
                "status": BlikDepositStatus.AWAITING_PROOF.value,
                "updated_at": now(),
            }
        },
    )
    return {
        "ok": True,
        "uploadUrl": _confirm_url(doc["upload_token"]),
        "recipientNotified": False,
    }


async def submit_manual_code(deposit_id: int, user_id: int, code: str) -> dict[str, Any]:
    doc = await _get_deposit_for_user(deposit_id, user_id)
    if doc["flow"] != BlikDepositFlow.MANUAL_CODE.value:
        raise HTTPException(status_code=400, detail="invalid_flow")
    if doc["status"] != BlikDepositStatus.MANUAL_PENDING.value:
        raise HTTPException(status_code=400, detail="invalid_status")
    normalized = normalize_blik_code(code)
    if not normalized:
        raise HTTPException(status_code=400, detail="invalid_blik_code")

    await get_db().blik_deposits.update_one(
        {"id": deposit_id},
        {
            "$set": {
                "manual_code": format_blik_code(normalized),
                "status": BlikDepositStatus.MANUAL_SUBMITTED.value,
                "updated_at": now(),
            }
        },
    )
    return {"ok": True, "status": BlikDepositStatus.MANUAL_SUBMITTED.value}


async def get_deposit_by_token(token: str) -> dict[str, Any]:
    doc = await get_db().blik_deposits.find_one({"upload_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="not_found")
    if doc["status"] == BlikDepositStatus.EXPIRED.value:
        raise HTTPException(status_code=410, detail="expired")
    expires = as_utc(doc.get("expires_at"))
    if expires and now() > expires:
        await get_db().blik_deposits.update_one(
            {"id": doc["id"]},
            {"$set": {"status": BlikDepositStatus.EXPIRED.value, "updated_at": now()}},
        )
        raise HTTPException(status_code=410, detail="expired")
    return {
        "id": doc["id"],
        "amountPln": str(doc["amount_pln"]),
        "status": doc["status"],
        "canUpload": doc["status"] == BlikDepositStatus.AWAITING_PROOF.value,
        "flow": doc["flow"],
        "matchedWithdraw": bool(doc.get("matched_withdraw_id")),
    }


async def upload_proof(token: str, file: UploadFile) -> dict[str, Any]:
    doc = await get_db().blik_deposits.find_one({"upload_token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="not_found")
    if doc["status"] != BlikDepositStatus.AWAITING_PROOF.value:
        raise HTTPException(status_code=400, detail="invalid_status")
    if doc["proof_attempts"] >= MAX_PROOF_ATTEMPTS:
        raise HTTPException(status_code=400, detail="too_many_attempts")

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _CONTENT_TYPE_KIND:
        raise HTTPException(status_code=400, detail="invalid_file_type")

    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="file_too_large")

    sniffed = _sniff_file_kind(data)
    expected = _CONTENT_TYPE_KIND[content_type]
    if sniffed is None or sniffed != expected:
        raise HTTPException(status_code=400, detail="file_content_mismatch")

    ext = (
        ".pdf"
        if sniffed == "application/pdf"
        else ".webp"
        if sniffed == "image/webp"
        else ".png"
        if sniffed == "image/png"
        else ".jpg"
    )
    dest = _upload_dir() / f"{doc['id']}_{secrets.token_hex(8)}{ext}"
    dest.write_bytes(data)

    await get_db().blik_deposits.update_one(
        {"id": doc["id"]},
        {
            "$set": {
                "status": BlikDepositStatus.VERIFYING.value,
                "proof_path": str(dest),
                "updated_at": now(),
            },
            "$inc": {"proof_attempts": 1},
        },
    )

    # Matched deposits fund a BLIK phone withdrawal — always require real document checks.
    matched_withdraw = bool(doc.get("matched_withdraw_id"))

    strict = True if matched_withdraw else get_settings().blik_verify_strict
    result = verify_blik_proof(
        dest,
        expected_amount=Decimal(str(doc["amount_pln"])),
        expected_phone=doc.get("withdraw_phone"),
        content_type=content_type,
        strict=strict,
    )

    if result["ok"] and _proof_ok_for_finalize(result, matched_withdraw=matched_withdraw):
        await _finalize_deposit_confirmed(doc["id"], result)
        dep_id = doc["id"]
        amount = doc["amount_pln"]
        msg_discord = (
            f"✅ **BLIK deposit #{dep_id} confirmed**\n\n"
            f"**Amount:** {amount} PLN\n"
            f"Your balance on **czutkabet.com** has been updated."
        )
        msg_telegram = (
            f"✅ <b>BLIK deposit #{dep_id} confirmed</b>\n\n"
            f"<b>Amount:</b> {amount} PLN\n"
            f"Your balance on <b>czutkabet.com</b> has been updated."
        )
        await notify_deposit_event(
            discord_id=doc.get("discord_id"),
            telegram_id=doc.get("telegram_id"),
            message=msg_discord,
            telegram_message=msg_telegram,
        )
        return {"ok": True, "status": "confirmed", "verification": result}

    await get_db().blik_deposits.update_one(
        {"id": doc["id"]},
        {
            "$set": {
                "status": BlikDepositStatus.PROOF_REJECTED.value,
                "proof_verification": result,
                "updated_at": now(),
            }
        },
    )
    attempts_left = MAX_PROOF_ATTEMPTS - doc["proof_attempts"] - 1
    if attempts_left > 0:
        await get_db().blik_deposits.update_one(
            {"id": doc["id"]},
            {"$set": {"status": BlikDepositStatus.AWAITING_PROOF.value}},
        )
    return {
        "ok": False,
        "status": "proof_rejected",
        "reason": result.get("reason"),
        "attemptsLeft": max(attempts_left, 0),
        "verification": result,
    }


async def admin_redeem_manual(deposit_id: int, success: bool, note: str | None = None) -> dict:
    doc = await get_db().blik_deposits.find_one({"id": deposit_id})
    if not doc:
        raise HTTPException(status_code=404, detail="not_found")
    if doc["flow"] != BlikDepositFlow.MANUAL_CODE.value:
        raise HTTPException(status_code=400, detail="invalid_flow")
    if doc["status"] != BlikDepositStatus.MANUAL_SUBMITTED.value:
        raise HTTPException(status_code=400, detail="invalid_status")

    if success:
        await _finalize_deposit_confirmed(deposit_id, {"reason": "admin_approved", "ok": True})
        msg_discord = (
            f"✅ **BLIK code approved** — deposit #{deposit_id}\n\n"
            f"**+{doc['amount_pln']} PLN** added to your balance."
        )
        msg_telegram = (
            f"✅ <b>BLIK code approved</b> — deposit #{deposit_id}\n\n"
            f"<b>+{doc['amount_pln']} PLN</b> added to your balance."
        )
    else:
        await get_db().blik_deposits.update_one(
            {"id": deposit_id},
            {
                "$set": {
                    "status": BlikDepositStatus.FAILED.value,
                    "admin_note": note,
                    "updated_at": now(),
                }
            },
        )
        msg_discord = f"❌ **BLIK code rejected** — deposit #{deposit_id} was not credited."
        msg_telegram = f"❌ <b>BLIK code rejected</b> — deposit #{deposit_id} was not credited."
        if note:
            msg_discord += f"\n**Reason:** {note}"
            msg_telegram += f"\n<b>Reason:</b> {note}"

    await notify_deposit_event(
        discord_id=doc.get("discord_id"),
        telegram_id=doc.get("telegram_id"),
        message=msg_discord,
        telegram_message=msg_telegram,
    )
    return {"ok": True, "status": "confirmed" if success else "failed"}


def _proof_ok_for_finalize(verification: dict, *, matched_withdraw: bool) -> bool:
    """Phone BLIK payouts require OCR/PDF proof with amount + recipient match."""
    if not verification.get("ok"):
        return False
    if not matched_withdraw:
        return True
    return verification.get("reason") == "verified"


async def record_recipient_confirmation(
    deposit_id: int,
    user_id: int,
    *,
    received: bool,
) -> dict[str, Any]:
    """Withdrawal owner confirms whether BLIK arrived on their phone."""
    doc = await get_db().blik_deposits.find_one({"id": deposit_id})
    if not doc:
        raise HTTPException(status_code=404, detail="not_found")
    wid = doc.get("matched_withdraw_id")
    if not wid:
        raise HTTPException(status_code=400, detail="not_matched_deposit")

    withdraw = await get_db().blik_withdrawals.find_one({"id": wid})
    if not withdraw or withdraw["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="not_withdraw_owner")

    if doc["status"] != BlikDepositStatus.CONFIRMED.value:
        raise HTTPException(status_code=400, detail="deposit_not_confirmed")
    if not doc.get("recipient_confirm_notified_at"):
        raise HTTPException(status_code=400, detail="recipient_not_notified")

    if doc.get("recipient_confirmed") is not None:
        return {
            "ok": True,
            "alreadyAnswered": True,
            "received": doc.get("recipient_confirmed"),
        }

    await get_db().blik_deposits.update_one(
        {"id": deposit_id},
        {
            "$set": {
                "recipient_confirmed": received,
                "recipient_confirmed_at": now(),
                "updated_at": now(),
            }
        },
    )

    depositor_id = int(doc["user_id"])

    if not received:
        await _set_blik_withdraw_blocked(depositor_id, True)
        return {"ok": True, "received": False, "status": "depositor_withdraw_blocked"}

    return {"ok": True, "received": True, "status": "depositor_withdraw_unlocked"}


async def _finalize_deposit_confirmed(deposit_id: int, verification: dict) -> None:
    doc = await get_db().blik_deposits.find_one({"id": deposit_id})
    if not doc or doc["status"] == BlikDepositStatus.CONFIRMED.value:
        return

    matched_withdraw = bool(doc.get("matched_withdraw_id"))
    if matched_withdraw and not _proof_ok_for_finalize(verification, matched_withdraw=True):
        log.warning(
            "refusing BLIK withdraw finalize without verified proof dep=%s wid=%s",
            deposit_id,
            doc.get("matched_withdraw_id"),
        )
        return

    pln = Decimal(str(doc["amount_pln"]))
    depositor_id = int(doc["user_id"])
    if matched_withdraw and doc.get("recipient_confirmed") is False:
        await _set_blik_withdraw_blocked(depositor_id, True)

    await get_db().users.update_one(
        {"id": depositor_id},
        {"$inc": {"balance_pln": pln, "playthrough_base_pln": pln}},
    )
    await get_db().blik_deposits.update_one(
        {"id": deposit_id},
        {
            "$set": {
                "status": BlikDepositStatus.CONFIRMED.value,
                "proof_verification": verification,
                "confirmed_at": now(),
                "updated_at": now(),
            }
        },
    )

    wid = doc.get("matched_withdraw_id")
    if wid:
        await get_db().blik_withdrawals.update_one(
            {"id": wid},
            {
                "$set": {
                    "status": BlikWithdrawStatus.FULFILLED.value,
                    "updated_at": now(),
                }
            },
        )

    if matched_withdraw:
        fresh = await get_db().blik_deposits.find_one({"id": deposit_id})
        if fresh and not fresh.get("recipient_confirm_notified_at"):
            await notify_withdraw_recipient(fresh)


async def _get_deposit_for_user(deposit_id: int, user_id: int) -> dict:
    doc = await get_db().blik_deposits.find_one({"id": deposit_id, "user_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="not_found")
    expires = as_utc(doc.get("expires_at"))
    if expires and now() > expires and doc["status"] not in (
        BlikDepositStatus.CONFIRMED.value,
        BlikDepositStatus.FAILED.value,
    ):
        await get_db().blik_deposits.update_one(
            {"id": deposit_id},
            {"$set": {"status": BlikDepositStatus.EXPIRED.value, "updated_at": now()}},
        )
        raise HTTPException(status_code=410, detail="expired")
    return doc


def parse_pln(raw: str) -> Decimal:
    try:
        v = Decimal(str(raw).strip().replace(",", "."))
        if v <= 0:
            raise ValueError()
        return v.quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as e:
        raise HTTPException(status_code=400, detail="invalid_amount") from e
