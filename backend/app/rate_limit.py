"""Shared slowapi limiter — keyed by client IP."""
from __future__ import annotations

from fastapi import HTTPException, Request
from slowapi import Limiter

from .client_ip import get_client_ip
from .distributed_rate import enforce_distributed_rate


def _limiter_key(request: Request) -> str:
    return get_client_ip(request)


limiter = Limiter(key_func=_limiter_key, default_limits=["240/minute"])

# Backward-compatible alias — uses trusted-proxy client IP when configured.
get_remote_address = get_client_ip


async def rate_limit_request(request: Request, route_key: str, per_minute: int) -> None:
    """Per-route Mongo-backed limit (shared across workers)."""
    await enforce_distributed_rate(get_client_ip(request), route_key, per_minute)


def enforce_route_rate(
    client_key: str,
    route_key: str,
    limit: int,
    window_sec: int = 60,
) -> None:
    """Sync fallback — use rate_limit_request in async handlers."""
    raise HTTPException(
        status_code=500,
        detail="use async rate_limit_request",
    )
