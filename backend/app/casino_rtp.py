"""Casino outcome helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from random import Random

TARGET_RTP = 0.80
LEGACY_FACTOR = 99
ACTUAL_FACTOR = 80
LEGACY_PAYOUT_EDGE = 0.99
KENO_FAIR_RTP_BY_PICKS: dict[int, float] = {
    1: 0.8715,
    2: 0.9405,
    3: 0.9920,
    4: 0.9514,
    5: 0.9241,
    6: 0.1968,
    7: 0.2120,
    8: 0.3269,
    9: 0.5886,
    10: 0.9452,
}
KENO_WEIGHT_AT_TARGET: dict[int, float] = {
    1: 0.8917,
    2: 0.9879,
    3: 0.9497,
    4: 0.9645,
    5: 0.9391,
    6: 1.5789,
    7: 1.6843,
    8: 1.4407,
    9: 1.1277,
    10: 0.9206,
}
BJ_DEALER_INIT_BIAS_RATE = 0.26
DICE_ROLL_EPS = 0.01


def resolve_rtp(user: dict | None) -> float:
    """Per-user override (0–1) or site default."""
    if not user:
        return TARGET_RTP
    raw = user.get("casino_rtp")
    if raw is None:
        return TARGET_RTP
    try:
        rtp = float(raw)
    except (TypeError, ValueError):
        return TARGET_RTP
    return max(0.01, min(0.99, rtp))


def actual_factor(rtp: float) -> int:
    return max(1, min(99, int(round(rtp * 100))))


def keno_pick_weight(rtp: float, n_picks: int) -> float:
    """Draw weight for Keno."""
    n = max(1, min(10, int(n_picks)))
    fair = KENO_FAIR_RTP_BY_PICKS[n]
    w_target = KENO_WEIGHT_AT_TARGET[n]
    denom = TARGET_RTP - fair
    if abs(denom) < 1e-9:
        return w_target
    w = 1.0 + (rtp - fair) * ((w_target - 1.0) / denom)
    return max(0.05, min(3.0, w))


def bj_dealer_bias_rate(rtp: float) -> float:
    if rtp <= 0:
        return BJ_DEALER_INIT_BIAS_RATE
    return max(0.0, min(1.0, BJ_DEALER_INIT_BIAS_RATE * (TARGET_RTP / rtp)))


def crash_payout_boost(rtp: float) -> float:
    """Crash cashout multiplier adjustment."""
    return rtp / TARGET_RTP if TARGET_RTP > 0 else 1.0


def seeded_pair() -> tuple[str, float, float]:
    """Returns ``(seed_hex, r1, r2)`` each in ``[0, 1)``."""
    seed = secrets.token_hex(32)
    digest = hmac.new(seed.encode(), b"roll", hashlib.sha256).digest()
    r1 = int.from_bytes(digest[:8], "big") / 2**64
    r2 = int.from_bytes(digest[8:16], "big") / 2**64
    return seed, r1, r2


def crash_multiplier(r: float, *, rtp: float | None = None) -> float:
    """Limbo / Crash result multiplier."""
    factor = actual_factor(rtp if rtp is not None else TARGET_RTP)
    return max(1.0, round(factor / max(r * 100, 1), 2))


def dice_roll_and_win(
    over: float,
    r1: float,
    r2: float,
    *,
    rtp: float | None = None,
) -> tuple[float, bool]:
    """Dice roll and win check."""
    target = rtp if rtp is not None else TARGET_RTP
    win_chance = (100 - over) / 100
    if win_chance <= 0:
        return 0.0, False
    eff_win_p = win_chance * (target / LEGACY_PAYOUT_EDGE)
    won = r1 < eff_win_p
    if won:
        span = max(100 - over - DICE_ROLL_EPS, DICE_ROLL_EPS)
        roll = over + DICE_ROLL_EPS + r2 * span
    else:
        roll = r2 * over if over > 0 else 0.0
    return round(min(roll, 100.0), 2), won


BLITZ_DECK_SIZE = 36
BLITZ_UNIQUE_MIN = 5
BLITZ_UNIQUE_MAX = BLITZ_DECK_SIZE


def blitz_win_chance(unique: int) -> float:
    """Fair probability of ``unique`` distinct cards before a repeat."""
    n = max(BLITZ_UNIQUE_MIN, min(BLITZ_DECK_SIZE, int(unique)))
    p = 1.0
    for j in range(n):
        p *= (BLITZ_DECK_SIZE - j) / BLITZ_DECK_SIZE
    return p


def blitz_multiplier(unique: int, *, rtp: float | None = None) -> float:
    """Total-return multiplier: payout = stake × mult; profit = stake × (mult − 1)."""
    p = blitz_win_chance(unique)
    if p <= 0:
        return 1.0
    target = rtp if rtp is not None else TARGET_RTP
    # Scale base RTP mult by standard 0.99 edge so UI (~1.32× at 5 unique) matches payout.
    return round((target / p) * (LEGACY_PAYOUT_EDGE / TARGET_RTP), 2)


def _blitz_draw_pick(seed: str, counter: int) -> int:
    digest = hmac.new(seed.encode(), f"blitz:{counter}".encode(), hashlib.sha256).digest()
    return int.from_bytes(digest[:4], "big") % BLITZ_DECK_SIZE


def blitz_simulate(unique: int, seed: str, *, rtp: float | None = None) -> tuple[bool, list[int]]:
    """Blitz picks until win (N unique) or bust (repeat). Provably fair uniform draws."""
    del rtp
    n = max(BLITZ_UNIQUE_MIN, min(BLITZ_DECK_SIZE, int(unique)))
    revealed: set[int] = set()
    picks: list[int] = []
    counter = 0
    while len(revealed) < n:
        pick = _blitz_draw_pick(seed, counter)
        counter += 1
        picks.append(pick)
        if pick in revealed:
            return False, picks
        revealed.add(pick)
    return True, picks


def draw_keno(
    rng: Random,
    picks: set[int],
    *,
    cell_count: int = 40,
    draw_count: int = 10,
    pick_weight: float | None = None,
) -> set[int]:
    """Weighted Keno draw."""
    weight = pick_weight if pick_weight is not None else KENO_WEIGHT_AT_TARGET[5]
    remaining = list(range(cell_count))
    drawn: set[int] = set()
    for _ in range(draw_count):
        weights = [weight if c in picks else 1.0 for c in remaining]
        total = sum(weights)
        pick = rng.uniform(0, total)
        acc = 0.0
        chosen_idx = len(remaining) - 1
        for i, w in enumerate(weights):
            acc += w
            if pick < acc:
                chosen_idx = i
                break
        drawn.add(remaining.pop(chosen_idx))
    return drawn
