"""Resolve client IP behind reverse proxy when TRUSTED_PROXY is enabled."""
from __future__ import annotations

from fastapi import Request
from slowapi.util import get_remote_address

from .config import get_settings


def get_client_ip(request: Request) -> str:
    """Client IP for rate limiting — honors CF-Connecting-IP / X-Forwarded-For when trusted."""
    if not get_settings().trusted_proxy:
        return get_remote_address(request)
    cf = request.headers.get("CF-Connecting-IP", "").strip()
    if cf:
        return cf
    xff = request.headers.get("X-Forwarded-For", "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)
