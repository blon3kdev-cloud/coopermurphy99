"""Resource ownership checks for IDOR prevention."""
from __future__ import annotations

from fastapi import HTTPException

from .safe_url import normalize_username


def require_resource_owner(doc_user_id: int, current_user_id: int) -> None:
    if doc_user_id != current_user_id:
        raise HTTPException(status_code=404, detail="not_found")


def require_admin_target_username(raw: str) -> str:
    key = normalize_username(raw)
    if not key:
        raise HTTPException(status_code=422, detail="invalid username")
    return key
