#!/usr/bin/env python3
"""Grid / Monte Carlo search for Dice2 difficulty presets targeting 90% RTP.

Usage:
  python3 scripts/dice2_ab_test.py --trials 40000
  python3 scripts/dice2_ab_report.py   # verify hardcoded engine presets
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import itertools
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from random import Random
from statistics import mean, median, stdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.dice2_engine import DICE2_TARGET_RTP  # noqa: E402
from app.dice2_engine import (  # noqa: E402
    GOLDEN_INDEX,
    PATH_LEN,
    apply_roll,
    cashout_payout,
    roll_dice,
)

TARGET = DICE2_TARGET_RTP
PATH = [
    [0, 0], [0, 1], [0, 2], [0, 3],
    [1, 3], [2, 3], [3, 3],
    [3, 2], [3, 1], [3, 0],
    [2, 0], [1, 0],
]


@dataclass(frozen=True)
class BoardPreset:
    name: str
    deadly: frozenset[int]
    golden_mult: float
    mult_by_index: tuple[float | None, ...]  # len PATH_LEN; None = start/deadly/golden slot


def build_tiles(preset: BoardPreset) -> list[dict]:
    tiles: list[dict] = []
    for i in range(PATH_LEN):
        if i == 0:
            tiles.append({"start": True})
        elif i in preset.deadly:
            tiles.append({"deadly": True})
        elif i == GOLDEN_INDEX:
            tiles.append({"golden": True, "mult": preset.golden_mult})
        else:
            m = preset.mult_by_index[i]
            if m is None:
                raise ValueError(f"missing mult at index {i} for {preset.name}")
            tiles.append({"mult": m})
    return tiles


def simulate_round(
    tiles: list[dict],
    seed: str,
    *,
    cash_after_safe: int = 1,
    max_rolls: int = 40,
) -> tuple[float, dict]:
    """Returns (payout, stats)."""
    path_pos = 0
    combined_mult = 1.0
    roll_index = 0
    safe_hits = 0
    dice_sums: list[int] = []
    steps_total = 0
    busted = False

    while roll_index < max_rolls:
        die_a, die_b = roll_dice(seed, roll_index)
        dice_sums.append(die_a + die_b)
        path_pos, combined_mult, busted, tile_mult = apply_roll(
            tiles, path_pos, combined_mult, die_a, die_b,
        )
        steps_total += die_a + die_b
        roll_index += 1
        if busted:
            return 0.0, {
                "busted": True,
                "rolls": roll_index,
                "dice_avg": mean(dice_sums),
                "steps": steps_total,
                "final_mult": combined_mult,
            }
        safe_hits += 1
        if safe_hits >= cash_after_safe:
            payout = cashout_payout(1.0, combined_mult)
            return payout, {
                "busted": False,
                "rolls": roll_index,
                "dice_avg": mean(dice_sums),
                "steps": steps_total,
                "final_mult": combined_mult,
                "tile_mult": tile_mult,
            }

    payout = cashout_payout(1.0, combined_mult)
    return payout, {
        "busted": False,
        "rolls": roll_index,
        "dice_avg": mean(dice_sums) if dice_sums else 7.0,
        "steps": steps_total,
        "final_mult": combined_mult,
    }


def run_monte_carlo(
    preset: BoardPreset,
    trials: int,
    *,
    cash_after_safe: int = 1,
) -> dict:
    tiles = build_tiles(preset)
    payouts: list[float] = []
    busts = 0
    dice_avgs: list[float] = []
    final_mults: list[float] = []
    rolls: list[int] = []

    for i in range(trials):
        seed = f"ab-{preset.name}-{i}"
        pay, st = simulate_round(tiles, seed, cash_after_safe=cash_after_safe)
        payouts.append(pay)
        if st["busted"]:
            busts += 1
        dice_avgs.append(st["dice_avg"])
        final_mults.append(st["final_mult"])
        rolls.append(st["rolls"])

    rtp = mean(payouts)
    return {
        "rtp": rtp,
        "rtp_delta": rtp - TARGET,
        "bust_rate": busts / trials,
        "avg_dice_sum": mean(dice_avgs),
        "avg_final_mult": mean(final_mults),
        "median_final_mult": median(final_mults),
        "avg_rolls": mean(rolls),
        "payout_stdev": stdev(payouts) if len(payouts) > 1 else 0.0,
    }


# Base layout — indices 5,7 always flank golden; medium adds deadly at 2
MEDIUM_DEADLY = frozenset({2, 5, 7})
BASE_MULT_LAYOUT = {
    1: 1.49,
    2: 1.05,
    3: 1.00,
    4: 0.93,
    8: 0.84,
    9: 0.74,
    10: 1.12,
    11: 1.05,
}
MEDIUM_GOLDEN = 1.90


def preset_from_params(
    name: str,
    deadly: frozenset[int],
    mults: dict[int, float],
    golden: float,
) -> BoardPreset:
    by_idx: list[float | None] = [None] * PATH_LEN
    for i in range(1, PATH_LEN):
        if i == GOLDEN_INDEX or i in deadly:
            continue
        if i not in mults:
            raise ValueError(f"{name}: missing mult for safe index {i}")
        by_idx[i] = mults[i]
    return BoardPreset(name=name, deadly=deadly, golden_mult=golden, mult_by_index=tuple(by_idx))


def mults_for_deadly(deadly: frozenset[int], scale: float) -> dict[int, float]:
    return {
        i: round(m * scale, 2)
        for i, m in BASE_MULT_LAYOUT.items()
        if i not in deadly
    }


def generate_candidates() -> list[BoardPreset]:
    out: list[BoardPreset] = []

    easy_deadly_opts = [frozenset({5, 7}), frozenset({5, 7, 11})]
    hard_deadly_opts = [
        frozenset({2, 5, 7, 9}),
        frozenset({2, 5, 7, 9, 11}),
        frozenset({1, 2, 5, 7, 9}),
        frozenset({2, 4, 5, 7, 9}),
    ]

    for deadly, g_mult, m_scale in itertools.product(
        easy_deadly_opts,
        [1.55, 1.70, 1.85],
        [0.82, 0.88, 0.94],
    ):
        mults = mults_for_deadly(deadly, m_scale)
        out.append(preset_from_params(f"easy-d{len(deadly)}-g{g_mult}-m{m_scale}", deadly, mults, g_mult))

    for g_mult, m_scale in itertools.product([1.85, 1.90, 1.95], [0.96, 1.0, 1.04]):
        mults = mults_for_deadly(MEDIUM_DEADLY, m_scale)
        out.append(preset_from_params(f"medium-g{g_mult}-m{m_scale}", MEDIUM_DEADLY, mults, g_mult))

    for deadly, g_mult, m_scale in itertools.product(
        hard_deadly_opts,
        [2.05, 2.20, 2.35, 2.50],
        [1.05, 1.12, 1.18, 1.25],
    ):
        mults = mults_for_deadly(deadly, m_scale)
        out.append(preset_from_params(f"hard-d{len(deadly)}-g{g_mult}-m{m_scale}", deadly, mults, g_mult))

    return out


def pick_best(candidates: list[tuple[BoardPreset, dict]], top_n: int = 5) -> list[tuple[BoardPreset, dict]]:
    return sorted(candidates, key=lambda x: abs(x[1]["rtp"] - TARGET))[:top_n]


def main() -> None:
    parser = argparse.ArgumentParser(description="Dice2 A/B RTP search")
    parser.add_argument("--trials", type=int, default=25_000)
    parser.add_argument("--cash-after", type=int, default=1)
    parser.add_argument("--json", action="store_true", help="Print winning presets as JSON")
    args = parser.parse_args()

    candidates = generate_candidates()
    print(f"Testing {len(candidates)} presets × {args.trials} trials (cash after {args.cash_after} safe roll)\n")

    buckets: dict[str, list[tuple[BoardPreset, dict]]] = {
        "easy": [],
        "medium": [],
        "hard": [],
    }

    for preset in candidates:
        tier = preset.name.split("-", 1)[0]
        stats = run_monte_carlo(preset, args.trials, cash_after_safe=args.cash_after)
        buckets[tier].append((preset, stats))

    winners: dict[str, BoardPreset] = {}
    for tier in ("easy", "medium", "hard"):
        best = pick_best(buckets[tier], top_n=8)
        print(f"═══ {tier.upper()} (top {len(best)}) ═══")
        for preset, st in best:
            print(
                f"  {preset.name}: RTP={st['rtp']:.4f} (Δ{st['rtp_delta']:+.4f}) "
                f"bust={st['bust_rate']:.3f} avgDice={st['avg_dice_sum']:.3f} "
                f"avgMult={st['avg_final_mult']:.3f} medMult={st['median_final_mult']:.2f}"
            )
        winners[tier] = best[0][0]
        print()

    # Multi-strategy report on winners
    print("═══ WINNERS — multi cashout strategy ═══")
    for tier, preset in winners.items():
        print(f"\n{tier}: {preset.name}")
        for n in (1, 2, 3):
            st = run_monte_carlo(preset, args.trials, cash_after_safe=n)
            print(f"  cash@{n}: RTP={st['rtp']:.4f} bust={st['bust_rate']:.3f} avgMult={st['avg_final_mult']:.3f}")

    if args.json:
        export = {}
        for tier, preset in winners.items():
            mults = {i: preset.mult_by_index[i] for i in range(PATH_LEN) if preset.mult_by_index[i] is not None}
            export[tier] = {
                "deadly": sorted(preset.deadly),
                "golden_mult": preset.golden_mult,
                "mults": mults,
            }
        print("\n" + json.dumps(export, indent=2))

    from app.dice2_engine import DIFFICULTIES, build_board as engine_build_board  # noqa: WPS433

    print("═══ ENGINE HARDCODE (post-tune check) ═══")
    for diff in DIFFICULTIES:
        tiles = engine_build_board(difficulty=diff)
        deadly = frozenset(i for i, t in enumerate(tiles) if t.get("deadly"))
        golden = float(next(t["mult"] for t in tiles if t.get("golden")))
        mults = {
            i: float(t["mult"])
            for i, t in enumerate(tiles)
            if t.get("mult") is not None and not t.get("golden")
        }
        preset = preset_from_params(diff, deadly, mults, golden)
        st = run_monte_carlo(preset, min(args.trials, 30_000), cash_after_safe=args.cash_after)
        print(f"  {diff}: RTP={st['rtp']:.4f} bust={st['bust_rate']:.3f}")


if __name__ == "__main__":
    main()
