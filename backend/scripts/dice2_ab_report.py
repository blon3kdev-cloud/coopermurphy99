#!/usr/bin/env python3
"""Detailed Dice2 difficulty report (RTP, dice stats, bust rates)."""
from __future__ import annotations

import sys
from pathlib import Path
from statistics import mean, median

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dice2_engine import DICE2_TARGET_RTP  # noqa: E402
from app.dice2_engine import DIFFICULTIES, build_board, roll_dice  # noqa: E402
from scripts.dice2_ab_test import simulate_round  # noqa: E402

TRIALS = 80_000


def report_difficulty(difficulty: str) -> None:
    tiles = build_board(difficulty=difficulty)
    deadly_n = sum(1 for t in tiles if t.get("deadly"))
    golden = next(t["mult"] for t in tiles if t.get("golden"))
    safe_mults = [t["mult"] for t in tiles if t.get("mult") and not t.get("golden")]

    print(f"\n{'═' * 60}")
    print(f"  {difficulty.upper()}  (target RTP {DICE2_TARGET_RTP:.0%})")
    print(f"{'═' * 60}")
    print(f"  Deadly tiles: {deadly_n}  |  Golden: {golden:.2f}x")
    print(f"  Safe tile mults: min {min(safe_mults):.2f}x  max {max(safe_mults):.2f}x  avg {mean(safe_mults):.2f}x")

    for cash_after in (1, 2, 3):
        payouts: list[float] = []
        busts = 0
        dice_sums: list[float] = []
        steps_list: list[int] = []
        final_mults: list[float] = []

        for i in range(TRIALS):
            pay, st = simulate_round(tiles, f"rpt-{difficulty}-{i}", cash_after_safe=cash_after)
            payouts.append(pay)
            if st["busted"]:
                busts += 1
            dice_sums.append(st["dice_avg"])
            steps_list.append(st["steps"])
            final_mults.append(st["final_mult"])

        rtp = mean(payouts)
        print(f"\n  Cash after {cash_after} safe roll(s):")
        print(f"    RTP .............. {rtp:.4f}  (Δ {rtp - DICE2_TARGET_RTP:+.4f})")
        print(f"    Bust rate ........ {busts / TRIALS:.3f}")
        print(f"    Avg dice sum/roll  {mean(dice_sums):.3f}  (fair = 7.000)")
        print(f"    Avg steps/round .. {mean(steps_list):.2f}")
        print(f"    Avg final mult ... {mean(final_mults):.3f}  med {median(final_mults):.2f}x")

    # Theoretical single-roll dice distribution (uniform d6×2)
    dist: dict[int, int] = {}
    for a in range(1, 7):
        for b in range(1, 7):
            dist[a + b] = dist.get(a + b, 0) + 1
    print("\n  Fair 2d6 sum distribution (probability):")
    for s in range(2, 13):
        p = dist.get(s, 0) / 36
        bar = "█" * int(p * 80)
        print(f"    {s:2d}: {p:5.1%} {bar}")


def main() -> None:
    print(f"Dice2 difficulty report — {TRIALS:,} trials per strategy")
    for d in DIFFICULTIES:
        report_difficulty(d)
    print()


if __name__ == "__main__":
    main()
