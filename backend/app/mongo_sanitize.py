"""Reject MongoDB operator keys in user-supplied dicts."""
from __future__ import annotations

from typing import Any

from fastapi import HTTPException


def _check_key(key: str) -> None:
    if key.startswith("$") or "." in key:
        raise HTTPException(status_code=422, detail="invalid field in payload")


def reject_operators(obj: Any, *, depth: int = 0) -> None:
    if depth > 12:
        raise HTTPException(status_code=422, detail="payload too deep")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _check_key(str(k))
            reject_operators(v, depth=depth + 1)
    elif isinstance(obj, list):
        for item in obj:
            reject_operators(item, depth=depth + 1)
