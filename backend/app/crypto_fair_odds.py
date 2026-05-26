"""Dynamic fair crypto odds from recent BTC price movement + log-normal model."""
from __future__ import annotations

import math
from typing import Any, Literal

from .btc_price_samples import BtcPriceSamples, MAX_SAMPLES
from .crypto_odds import (
    CRYPTO_BTC_VOL,
    calc_crypto_odds_with_vol,
    time_fraction,
    time_urgency_scale,
    window_seconds,
)

SECS_PER_YEAR = 365.25 * 24 * 3600
MIN_SAMPLES_DYNAMIC = 5
OBSERVED_BLEND = 0.65
# Never quote below baseline σ — quiet ticks stay dampened; only raise σ when price actually moves.
VOL_CEIL = 3.20
TREND_THRESHOLD_PCT = 0.008


def _realized_annual_vol(samples: list) -> float | None:
    """Annualized σ from irregular log-return samples."""
    if len(samples) < 2:
        return None
    sum_r2 = 0.0
    sum_dt = 0.0
    for i in range(1, len(samples)):
        p0, p1 = samples[i - 1].price, samples[i].price
        dt = (samples[i].ts_ms - samples[i - 1].ts_ms) / 1000.0
        if p0 <= 0 or p1 <= 0 or dt <= 0:
            continue
        r = math.log(p1 / p0)
        sum_r2 += r * r
        sum_dt += dt
    if sum_dt <= 0 or sum_r2 <= 0:
        return None
    var_per_sec = sum_r2 / sum_dt
    return math.sqrt(var_per_sec * SECS_PER_YEAR)


def _movement_summary(samples: list) -> dict[str, Any]:
    if len(samples) < 2:
        return {
            "trend": "flat",
            "recentMovePct": 0.0,
            "spanSec": 0.0,
            "sampleCount": len(samples),
        }
    first, last = samples[0], samples[-1]
    span_sec = max(0.0, (last.ts_ms - first.ts_ms) / 1000.0)
    move_pct = 0.0
    if first.price > 0:
        move_pct = ((last.price - first.price) / first.price) * 100.0
    if move_pct > TREND_THRESHOLD_PCT:
        trend: Literal["flat", "up", "down"] = "up"
    elif move_pct < -TREND_THRESHOLD_PCT:
        trend = "down"
    else:
        trend = "flat"
    return {
        "trend": trend,
        "recentMovePct": round(move_pct, 4),
        "spanSec": round(span_sec, 1),
        "sampleCount": len(samples),
    }


class CryptoFairOddsService:
    """Tracks last feed prices and quotes Higher/Lower from observed + baseline vol."""

    def __init__(self) -> None:
        self._samples = BtcPriceSamples(MAX_SAMPLES)

    def record_price(self, price: float, ts_ms: int) -> None:
        self._samples.record(price, ts_ms)

    def effective_vol(self) -> float:
        samples = self._samples.list()
        observed = _realized_annual_vol(samples)
        if observed is None or len(samples) < MIN_SAMPLES_DYNAMIC:
            return CRYPTO_BTC_VOL
        blended = OBSERVED_BLEND * observed + (1.0 - OBSERVED_BLEND) * CRYPTO_BTC_VOL
        return max(CRYPTO_BTC_VOL, min(VOL_CEIL, blended))

    def fair_odds_meta(self) -> dict[str, Any]:
        samples = self._samples.list()
        observed = _realized_annual_vol(samples)
        movement = _movement_summary(samples)
        eff = self.effective_vol()
        return {
            **movement,
            "baselineVol": round(CRYPTO_BTC_VOL, 3),
            "observedVol": round(observed, 3) if observed is not None else None,
            "effectiveVol": round(eff, 3),
            "dynamic": len(samples) >= MIN_SAMPLES_DYNAMIC and observed is not None,
        }

    def calc_odds(
        self,
        current: float,
        openp: float,
        remaining_sec: float,
        *,
        window: str | None = None,
    ) -> dict[str, float]:
        vol = self.effective_vol()
        wsec = window_seconds(window)
        return calc_crypto_odds_with_vol(
            vol,
            current,
            openp,
            remaining_sec,
            window_sec=wsec,
        )

    def odds_context(
        self,
        remaining_sec: float,
        *,
        window: str | None = None,
    ) -> dict[str, Any]:
        wsec = window_seconds(window)
        frac = time_fraction(remaining_sec, wsec)
        scale = time_urgency_scale(remaining_sec, wsec)
        return {
            "window": window,
            "windowSec": wsec,
            "remainingSec": round(max(0.0, remaining_sec), 1),
            "timeFraction": round(frac, 4) if frac is not None else None,
            "timeScale": round(scale, 4),
            "effectiveVol": round(self.effective_vol(), 3),
        }

    def snapshot_extras(self) -> dict[str, Any]:
        return {
            "priceSamples": self._samples.as_dicts(),
            "fairOdds": self.fair_odds_meta(),
        }


fair_odds_service = CryptoFairOddsService()


def calc_fair_crypto_odds(
    current: float,
    openp: float,
    remaining_sec: float,
    *,
    window: str | None = None,
) -> dict[str, float]:
    return fair_odds_service.calc_odds(
        current,
        openp,
        remaining_sec,
        window=window,
    )
