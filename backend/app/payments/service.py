"""Payment lifecycle — create, watch, confirm."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any, Optional

import httpx

from ..config import get_settings
from ..db import as_utc, get_db, next_id, now
from .derivation import derive_address
from .matching import on_deposit_confirmed, try_match_deposit
from .matching import check_matched_deposit
from .monitors import check_payment_received
from .sweep import SweepDeferred, sweep_payment
from .qr import format_amount, qr_ascii, qr_payload, save_qr_png
from .types import (
    ASSET_SYMBOLS,
    PaymentAsset,
    PaymentKind,
    PaymentStatus,
    require_asset_enabled,
)

log = logging.getLogger(__name__)


class PaymentService:
    @staticmethod
    async def create_deposit(
        asset: PaymentAsset,
        amount: Decimal,
        user_id: Optional[int] = None,
        *,
        amount_pln: Optional[Decimal] = None,
    ) -> dict[str, Any]:
        require_asset_enabled(asset)
        settings = get_settings()
        payment_id = await next_id("crypto_payments")
        expires_at = now() + timedelta(minutes=settings.payment_timeout_min)

        match = await try_match_deposit(asset, amount, amount_pln=amount_pln)
        if match:
            derivation_index = None
            address = match["address"]
            pay_amount = match["amount_expected"]
            pay_pln = match.get("amount_pln")
        else:
            derivation_index = await next_id("payment_derivation_index")
            address = derive_address(asset, derivation_index)
            pay_amount = amount
            pay_pln = amount_pln

        doc = {
            "id": payment_id,
            "kind": PaymentKind.DEPOSIT.value,
            "asset": asset.value,
            "amount_expected": pay_amount,
            "amount_pln": float(pay_pln) if pay_pln is not None else None,
            "amount_received": None,
            "derivation_index": derivation_index,
            "address": address,
            "destination_address": None,
            "matched_withdraw_id": match.get("matched_withdraw_id") if match else None,
            "address_balance_baseline": match.get("address_balance_baseline") if match else None,
            "funds_user_address": bool(match),
            "status": PaymentStatus.PENDING.value,
            "tx_ids": [],
            "confirmations": 0,
            "user_id": user_id,
            "created_at": now(),
            "expires_at": expires_at,
        }
        await get_db().crypto_payments.insert_one(doc)
        return doc

    @staticmethod
    async def create_withdraw(
        asset: PaymentAsset,
        amount: Decimal,
        destination_address: str,
        user_id: Optional[int] = None,
        *,
        amount_pln: Optional[Decimal] = None,
    ) -> dict[str, Any]:
        require_asset_enabled(asset)
        if user_id is not None and amount_pln is not None:
            db = get_db()
            user = await db.users.find_one({"id": user_id})
            if not user:
                raise ValueError("user not found")
            if user["balance_pln"] < amount_pln:
                raise ValueError("insufficient balance")
            updated = await db.users.find_one_and_update(
                {"id": user_id, "balance_pln": {"$gte": amount_pln}},
                {"$inc": {"balance_pln": -amount_pln}},
            )
            if not updated:
                raise ValueError("insufficient balance")

        payment_id = await next_id("crypto_payments")

        doc = {
            "id": payment_id,
            "kind": PaymentKind.WITHDRAW.value,
            "asset": asset.value,
            "amount_expected": amount,
            "amount_pln": float(amount_pln) if amount_pln is not None else None,
            "amount_filled": 0,
            "amount_received": None,
            "derivation_index": None,
            "address": None,
            "destination_address": destination_address.strip(),
            "status": PaymentStatus.PENDING.value,
            "tx_ids": [],
            "confirmations": 0,
            "user_id": user_id,
            "created_at": now(),
            "expires_at": None,
        }
        await get_db().crypto_payments.insert_one(doc)
        return doc

    @staticmethod
    async def get_payment(payment_id: int) -> Optional[dict[str, Any]]:
        return await get_db().crypto_payments.find_one({"id": payment_id})

    @staticmethod
    def format_deposit_instructions(doc: dict[str, Any], qr_path: Optional[str] = None) -> str:
        asset = PaymentAsset(doc["asset"])
        symbol = ASSET_SYMBOLS[asset]
        amount = doc["amount_expected"]
        address = doc["address"]
        lines = [
            "",
            f"Payment #{doc['id']} — {PaymentKind.DEPOSIT.value}",
            f"Asset:     {asset.value} ({symbol})",
            f"Amount:    {format_amount(amount, asset)} {symbol}",
            f"Address:   {address}",
            f"Expires:   {doc['expires_at']}",
            "",
            "QR (scan with wallet — encodes address only):",
            qr_ascii(qr_payload(address)),
        ]
        if qr_path:
            lines.append(f"QR PNG:    {qr_path}")
        return "\n".join(lines)

    @staticmethod
    async def watch_payment(
        payment_id: int,
        *,
        on_poll: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Poll chain until confirmed, expired, or timeout. Returns final payment doc."""
        settings = get_settings()
        doc = await PaymentService.get_payment(payment_id)
        if not doc:
            raise ValueError(f"payment {payment_id} not found")
        if doc["kind"] != PaymentKind.DEPOSIT.value:
            return doc

        asset = PaymentAsset(doc["asset"])
        expected = doc["amount_expected"]
        address = doc["address"]
        interval = settings.payment_poll_interval_sec

        async with httpx.AsyncClient() as client:
            while True:
                expires_at = as_utc(doc.get("expires_at"))
                if expires_at is not None and now() >= expires_at:
                    await PaymentService._set_status(
                        payment_id, PaymentStatus.EXPIRED
                    )
                    doc = await PaymentService.get_payment(payment_id) or doc
                    break

                try:
                    if doc.get("matched_withdraw_id"):
                        result = await check_matched_deposit(client, doc)
                    else:
                        result = await check_payment_received(
                            client, asset, address, expected
                        )
                except Exception as e:
                    log.warning("payment poll error id=%s: %s", payment_id, e)
                    result = None

                if result and result.confirmed:
                    doc = await PaymentService._confirm(
                        payment_id,
                        received=result.received,
                        tx_ids=result.tx_ids,
                        confirmations=result.confirmations,
                    )
                    break

                if result and on_poll:
                    on_poll(result.received, expected)

                await asyncio.sleep(interval)
                doc = await PaymentService.get_payment(payment_id) or doc
                if doc["status"] != PaymentStatus.PENDING.value:
                    break

        return doc

    @staticmethod
    async def _confirm(
        payment_id: int,
        *,
        received: Decimal,
        tx_ids: list[str],
        confirmations: int,
    ) -> dict[str, Any]:
        db = get_db()
        await db.crypto_payments.update_one(
            {"id": payment_id, "status": PaymentStatus.PENDING.value},
            {
                "$set": {
                    "status": PaymentStatus.CONFIRMED.value,
                    "amount_received": received,
                    "tx_ids": tx_ids,
                    "confirmations": confirmations,
                    "confirmed_at": now(),
                }
            },
        )
        doc = await PaymentService.get_payment(payment_id) or {}
        if doc.get("kind") == PaymentKind.DEPOSIT.value:
            await on_deposit_confirmed(doc)
        if doc and get_settings().payment_auto_sweep and not doc.get("funds_user_address"):
            await PaymentService.maybe_sweep_deposit(doc)
        return doc

    @staticmethod
    async def maybe_sweep_deposit(doc: dict[str, Any]) -> None:
        """
        Check on-chain balance on the deposit address.
        If enough: sweep everything to master. If not: mark waiting (no error spam).
        """
        payment_id = doc["id"]
        if doc.get("derivation_index") is None:
            return
        if doc.get("sweep_status") == "completed" and doc.get("sweep_tx_id"):
            return

        try:
            sweep_tx = await sweep_payment(doc, force=True)
            if sweep_tx:
                await get_db().crypto_payments.update_one(
                    {"id": payment_id},
                    {
                        "$set": {
                            "sweep_tx_id": sweep_tx,
                            "sweep_status": "completed",
                            "sweep_error": None,
                        }
                    },
                )
                log.info("payment %s swept to master tx=%s", payment_id, sweep_tx)
        except SweepDeferred as e:
            await get_db().crypto_payments.update_one(
                {"id": payment_id},
                {
                    "$set": {
                        "sweep_status": "waiting",
                        "sweep_error": str(e)[:500],
                    }
                },
            )
            log.info("payment %s sweep waiting: %s", payment_id, e)
        except Exception as e:
            log.exception("sweep failed payment %s: %s", payment_id, e)
            await get_db().crypto_payments.update_one(
                {"id": payment_id},
                {
                    "$set": {
                        "sweep_status": "failed",
                        "sweep_error": str(e)[:500],
                    }
                },
            )

    @staticmethod
    async def process_pending_sweeps(*, limit: int = 50) -> int:
        """Sweep confirmed deposits once their address holds enough funds."""
        db = get_db()
        cursor = db.crypto_payments.find(
            {
                "kind": PaymentKind.DEPOSIT.value,
                "status": PaymentStatus.CONFIRMED.value,
                "derivation_index": {"$ne": None},
                "funds_user_address": {"$ne": True},
                "sweep_status": {"$nin": ["completed"]},
            }
        ).sort("confirmed_at", 1).limit(limit)

        n = 0
        async for doc in cursor:
            await PaymentService.maybe_sweep_deposit(doc)
            n += 1
        return n

    @staticmethod
    async def _set_status(payment_id: int, status: PaymentStatus) -> None:
        await get_db().crypto_payments.update_one(
            {"id": payment_id},
            {"$set": {"status": status.value}},
        )
