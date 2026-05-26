"""Ring buffer of recent BTC/USD feed samples (last N price updates)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

MAX_SAMPLES = 30


@dataclass(frozen=True)
class PriceSample:
    ts_ms: int
    price: float

    def as_dict(self) -> dict[str, Any]:
        return {"ts": self.ts_ms, "price": round(self.price, 2)}


class BtcPriceSamples:
    def __init__(self, max_samples: int = MAX_SAMPLES) -> None:
        self._max = max(2, max_samples)
        self._buf: deque[PriceSample] = deque(maxlen=self._max)

    def record(self, price: float, ts_ms: int) -> None:
        if price <= 0:
            return
        p = round(float(price), 2)
        if self._buf and self._buf[-1].price == p and ts_ms - self._buf[-1].ts_ms < 500:
            return
        self._buf.append(PriceSample(ts_ms=int(ts_ms), price=p))

    def __len__(self) -> int:
        return len(self._buf)

    def list(self) -> list[PriceSample]:
        return list(self._buf)

    def as_dicts(self) -> list[dict[str, Any]]:
        return [s.as_dict() for s in self._buf]

    def clear(self) -> None:
        self._buf.clear()
