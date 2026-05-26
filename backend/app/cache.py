"""Simple in-process TTL cache for hot read endpoints."""
from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

T = TypeVar("T")

_store: dict[str, tuple[float, Any]] = {}


def get_cached(key: str) -> Any | None:
    entry = _store.get(key)
    if entry is None:
        return None
    expires, value = entry
    if time.monotonic() > expires:
        _store.pop(key, None)
        return None
    return value


def set_cached(key: str, value: Any, ttl_sec: float) -> None:
    _store[key] = (time.monotonic() + ttl_sec, value)


async def cached_async(key: str, ttl_sec: float, factory: Callable[[], Any]) -> Any:
    hit = get_cached(key)
    if hit is not None:
        return hit
    value = await factory()
    set_cached(key, value, ttl_sec)
    return value
