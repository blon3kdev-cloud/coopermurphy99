"""BLIK payment enums and helpers."""
from __future__ import annotations

from enum import Enum


class BlikDepositStatus(str, Enum):
    PENDING_SEND = "pending_send"
    AWAITING_PROOF = "awaiting_proof"
    VERIFYING = "verifying"
    CONFIRMED = "confirmed"
    PROOF_REJECTED = "proof_rejected"
    MANUAL_PENDING = "manual_pending"
    MANUAL_SUBMITTED = "manual_submitted"
    FAILED = "failed"
    EXPIRED = "expired"


class BlikWithdrawStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class BlikDepositFlow(str, Enum):
    MATCHED = "matched"
    MANUAL_CODE = "manual_code"
