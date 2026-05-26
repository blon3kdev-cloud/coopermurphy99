"""Map internal exceptions to stable API error codes — no raw exception strings to clients."""
from __future__ import annotations

import logging

from fastapi import HTTPException

log = logging.getLogger(__name__)

_VALUE_ERROR_CODES: dict[str, str] = {
    "user not found": "user_not_found",
    "insufficient balance": "insufficient_balance",
    "amount must be positive": "invalid_amount",
    "invalid asset": "invalid_asset",
    "round unavailable": "round_unavailable",
    "already bet this round": "already_bet",
    "already queued for next round": "already_queued",
    "not running": "not_running",
    "no active bet": "no_active_bet",
    "round crashed": "round_crashed",
    "no cancellable bet": "no_cancellable_bet",
}


def http_400_from_value_error(exc: ValueError) -> HTTPException:
    msg = str(exc).strip()
    code = _VALUE_ERROR_CODES.get(msg.lower())
    if code is None and msg.lower().startswith("payment ") and "not found" in msg.lower():
        code = "payment_not_found"
    if code is None and "decimal places" in msg.lower():
        code = "invalid_amount"
    if code is None and msg.lower().startswith("too many decimal"):
        code = "invalid_amount"
    if code is None:
        log.warning("unmapped ValueError for client response: %s", msg)
        code = "bad_request"
    return HTTPException(status_code=400, detail=code)
