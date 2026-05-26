"""BLIK code parsing — accepts ``123456`` or ``123 456`` (only digits, exactly 6)."""
from __future__ import annotations

import re


def normalize_blik_code(raw: str) -> str | None:
    """Strip non-digits; return 6-digit string or None."""
    digits = re.sub(r"\D", "", (raw or "").strip())
    if len(digits) != 6:
        return None
    return digits


def format_blik_code(digits: str) -> str:
    """Display as XXX XXX."""
    d = re.sub(r"\D", "", digits)
    if len(d) != 6:
        return digits
    return f"{d[:3]} {d[3:]}"
