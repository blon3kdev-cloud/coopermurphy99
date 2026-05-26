#!/usr/bin/env python3
"""Monte Carlo checks for casino games."""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.blackjack_engine import (  # noqa: E402
    compare_hands,
    deal_initial_dealer,
    draw,
    hand_value,
    is_bust,
    new_shoe,
    payout_for_outcome,
    play_dealer,
)
from app.casino_rtp import (  # noqa: E402
    LEGACY_PAYOUT_EDGE,
    TARGET_RTP,
    crash_multiplier,
    dice_roll_and_win,
    draw_keno,
    keno_pick_weight,
)
KENO_TABLE = {
    1: [0, 3.5],
    2: [0, 0, 15],
    3: [0, 0, 0, 80],
    4: [0, 0, 0, 12, 200],
    5: [0, 0, 0, 4.5, 45, 450],
    6: [0, 0, 0, 0, 6, 13, 450],
    7: [0, 0, 0, 0, 3, 8, 13, 500],
    8: [0, 0, 0, 0, 3, 6, 13, 40, 650],
    9: [0, 0, 0, 0, 3, 8, 13, 40, 400, 800],
    10: [0, 0, 0, 0, 3.5, 8, 13, 40, 400, 650, 1000],
}

ROUNDS = 50_000
STAKE = 1.0


def sim_limbo() -> float:
    total_payout = 0.0
    target = 2.0
    for _ in range(ROUNDS):
        r = random.random()
        crash = crash_multiplier(r)
        if crash >= target:
            total_payout += STAKE * target
    return total_payout / (ROUNDS * STAKE)


def sim_dice(over: float = 50.5) -> float:
    win_chance = (100 - over) / 100
    mult = LEGACY_PAYOUT_EDGE / win_chance
    total_payout = 0.0
    for _ in range(ROUNDS):
        r1, r2 = random.random(), random.random()
        _, won = dice_roll_and_win(over, r1, r2)
        if won:
            total_payout += STAKE * mult
    return total_payout / (ROUNDS * STAKE)


def sim_keno(n_picks: int) -> float:
    total_payout = 0.0
    row = KENO_TABLE[n_picks]
    for _ in range(ROUNDS):
        picks = set(random.sample(range(40), n_picks))
        drawn = draw_keno(
            random.Random(),
            picks,
            pick_weight=keno_pick_weight(TARGET_RTP, n_picks),
        )
        hits = sum(1 for p in picks if p in drawn)
        total_payout += STAKE * row[hits]
    return total_payout / (ROUNDS * STAKE)


def _basic_stand_threshold(dealer_up: int) -> int:
    return 17 if dealer_up >= 7 else 12


def sim_blackjack() -> float:
    total_payout = 0.0
    for _ in range(ROUNDS):
        deck = new_shoe()
        player = draw(deck, 2)
        dealer = deal_initial_dealer(deck)
        up_val = hand_value([dealer[0]])
        while hand_value(player) < _basic_stand_threshold(up_val) and not is_bust(player):
            player.extend(draw(deck, 1))
        if is_bust(player):
            outcome = "lose"
        else:
            dealer_final = play_dealer(deck, dealer)
            outcome = compare_hands(player, dealer_final)
        payout, _ = payout_for_outcome(STAKE, outcome)
        total_payout += payout
    return total_payout / (ROUNDS * STAKE)


def main() -> None:
    print(f"Target RTP: {TARGET_RTP:.0%}\n")
    limbo = sim_limbo()
    dice = sim_dice()
    print(f"Limbo (target 2.0x):  {limbo:.4f}")
    print(f"Dice (over 50.5):     {dice:.4f}")
    keno_rtps = [sim_keno(n) for n in range(1, 11)]
    keno_avg = sum(keno_rtps) / len(keno_rtps)
    print(f"Keno avg (1-10 picks): {keno_avg:.4f}")
    for n, rtp in enumerate(keno_rtps, 1):
        print(f"  {n} picks: {rtp:.4f}")
    bj = sim_blackjack()
    print(f"Blackjack (basic):    {bj:.4f}")


if __name__ == "__main__":
    main()
