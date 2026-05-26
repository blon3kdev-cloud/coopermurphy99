"""VIP bonus amounts from wagered volume and net loss (wagered − won)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# wagered × rate_wager + net_loss × rate_loss (both fractions of PLN)
BONUS_RATES: dict[str, tuple[Decimal, Decimal]] = {
    "daily": (Decimal("0.001"), Decimal("0.005")),
    "weekly": (Decimal("0.002"), Decimal("0.008")),
    "monthly": (Decimal("0.004"), Decimal("0.015")),
    "rank": (Decimal("0.008"), Decimal("0.025")),
}

BONUS_MIN_PLN: dict[str, Decimal] = {
    "daily": Decimal("0.50"),
    "weekly": Decimal("1"),
    "monthly": Decimal("3"),
    "rank": Decimal("5"),
}

BONUS_MAX_PLN: dict[str, Decimal] = {
    "daily": Decimal("25"),
    "weekly": Decimal("75"),
    "monthly": Decimal("200"),
    "rank": Decimal("150"),
}


def net_loss_pln(wagered: Decimal, won: Decimal) -> Decimal:
    """Net loss in the period: max(0, wagered − won)."""
    return max(Decimal(0), wagered - won)


@dataclass(frozen=True)
class BonusCalculation:
    kind: str
    wagered_pln: Decimal
    won_pln: Decimal
    net_loss_pln: Decimal
    raw_pln: Decimal
    amount_pln: Decimal


def calculate_bonus(
    kind: str,
    wagered: Decimal | float | str,
    won: Decimal | float | str = 0,
) -> BonusCalculation:
    """
    Bonus = wagered × rate_wager + net_loss × rate_loss, clamped to min/max.
    Returns amount_pln = 0 when there is no wager and no net loss.
    """
    if kind not in BONUS_RATES:
        raise ValueError(f"unknown bonus kind: {kind}")

    w = Decimal(str(wagered or 0))
    won_d = Decimal(str(won or 0))
    loss = net_loss_pln(w, won_d)
    rate_w, rate_l = BONUS_RATES[kind]
    raw = (w * rate_w + loss * rate_l).quantize(Decimal("0.01"))

    if w <= 0 and loss <= 0:
        amount = Decimal(0)
    else:
        amount = max(BONUS_MIN_PLN[kind], min(raw, BONUS_MAX_PLN[kind]))

    return BonusCalculation(
        kind=kind,
        wagered_pln=w,
        won_pln=won_d,
        net_loss_pln=loss,
        raw_pln=raw,
        amount_pln=amount,
    )
