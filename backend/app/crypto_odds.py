"""Crypto up/down odds — log-normal model with platform margin (shared by API + SSE)."""
from __future__ import annotations

import math

CRYPTO_MARGIN = 0.70
CRYPTO_MIN_ODDS = 1.1
# Annualized σ for log-normal scaling; tuned above spot vol so short-window
# ticks (often ≪0.1%) do not swing Higher/Lower quotes on noise alone.
CRYPTO_BTC_VOL = 1.60
SECS_PER_YEAR = 365.25 * 24 * 3600

# Must match frontend `cryptoWindowClock` / `btc_price._PERIOD_MS` (+ 24h).
WINDOW_SEC: dict[str, float] = {"5m": 300.0, "30m": 1800.0, "24h": 86400.0}
# Fraction of window left → scale on σ; higher = odds lock in harder near the buzzer.
TIME_URGENCY_EXP = 0.62
MIN_TIME_FRAC = 0.02


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))


def window_seconds(window: str | None) -> float | None:
    if not window:
        return None
    return WINDOW_SEC.get(window)


def time_urgency_scale(remaining_sec: float, window_sec: float | None) -> float:
    """<1 when the clock is low — less σ left → current lead matters more."""
    if window_sec is None or window_sec <= 0:
        return 1.0
    frac = max(MIN_TIME_FRAC, min(1.0, remaining_sec / window_sec))
    return frac**TIME_URGENCY_EXP


def time_fraction(remaining_sec: float, window_sec: float | None) -> float | None:
    if window_sec is None or window_sec <= 0:
        return None
    return max(MIN_TIME_FRAC, min(1.0, remaining_sec / window_sec))


def calc_crypto_odds_with_vol(
    annual_vol: float,
    current: float,
    openp: float,
    remaining_sec: float,
    *,
    window_sec: float | None = None,
) -> dict[str, float]:
    if current <= 0 or openp <= 0 or remaining_sec <= 0:
        return {"up": 1.40, "down": 1.40}
    vol = max(0.01, float(annual_vol))
    T = remaining_sec / SECS_PER_YEAR
    t_scale = time_urgency_scale(remaining_sec, window_sec)
    sig_sqrt_t = max(1e-9, vol * math.sqrt(T) * t_scale)
    d = math.log(current / openp) / sig_sqrt_t
    p_up = max(0.01, min(0.99, _norm_cdf(d)))
    p_down = 1 - p_up
    return {
        "up": round(min(15, max(1.01, CRYPTO_MARGIN / p_up)), 2),
        "down": round(min(15, max(1.01, CRYPTO_MARGIN / p_down)), 2),
    }


def calc_crypto_odds(
    current: float,
    openp: float,
    remaining_sec: float,
    *,
    window: str | None = None,
) -> dict[str, float]:
    return calc_crypto_odds_with_vol(
        CRYPTO_BTC_VOL,
        current,
        openp,
        remaining_sec,
        window_sec=window_seconds(window),
    )
