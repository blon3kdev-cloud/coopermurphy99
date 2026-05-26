"""Shared types for chain monitors."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MonitorResult:
    received: Decimal
    confirmed: bool
    tx_ids: list[str]
    confirmations: int
