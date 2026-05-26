"""Strip sensitive keys before logging structured extras."""
from __future__ import annotations

from typing import Any

_SENSITIVE = frozenset(
    {
        "password",
        "pin",
        "token",
        "authorization",
        "mnemonic",
        "secret",
        "code_hash",
        "internal_secret",
        "x-internal-secret",
    }
)


def redact_for_log(obj: Any, *, depth: int = 0) -> Any:
    if depth > 6:
        return "[truncated]"
    if isinstance(obj, dict):
        out: dict = {}
        for k, v in obj.items():
            key = str(k).lower()
            if key in _SENSITIVE or key.endswith("_hash") or key.endswith("_token"):
                out[k] = "[redacted]"
            else:
                out[k] = redact_for_log(v, depth=depth + 1)
        return out
    if isinstance(obj, list):
        return [redact_for_log(x, depth=depth + 1) for x in obj[:20]]
    return obj
