#!/usr/bin/env python3
"""Interactive Monte Carlo simulator for casino games."""
from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
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
    crash_multiplier,
    crash_payout_boost,
    dice_roll_and_win,
    draw_keno,
    keno_pick_weight,
    bj_dealer_bias_rate,
)
STAKE = 1.0
DRAW_COUNT = 10
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
DEFAULT_RTP_PCT = 80.0
DEFAULT_ROUNDS = 50_000

GAMES = ("limbo", "dice", "keno", "crash", "blackjack")


@dataclass
class SimResult:
    game: str
    rounds: int
    rtp_target: float
    total_wagered: float
    total_payout: float
    wins: int
    extra: dict

    @property
    def rtp_actual(self) -> float:
        return self.total_payout / self.total_wagered if self.total_wagered else 0.0

    @property
    def net(self) -> float:
        return self.total_payout - self.total_wagered

    @property
    def win_rate(self) -> float:
        return self.wins / self.rounds if self.rounds else 0.0


def _basic_stand_threshold(dealer_up: int) -> int:
    return 17 if dealer_up >= 7 else 12


def sim_limbo(rounds: int, rtp: float, *, target: float = 2.0) -> SimResult:
    payout = wins = 0.0
    for _ in range(rounds):
        r = random.random()
        crash = crash_multiplier(r, rtp=rtp)
        if crash >= target:
            payout += STAKE * target
            wins += 1
    return SimResult("limbo", rounds, rtp, rounds * STAKE, payout, int(wins), {"target": target})


def sim_dice(rounds: int, rtp: float, *, over: float = 50.5) -> SimResult:
    win_chance = (100 - over) / 100
    mult = LEGACY_PAYOUT_EDGE / win_chance if win_chance > 0 else 0
    payout = wins = 0.0
    for _ in range(rounds):
        r1, r2 = random.random(), random.random()
        _, won = dice_roll_and_win(over, r1, r2, rtp=rtp)
        if won:
            payout += STAKE * mult
            wins += 1
    return SimResult("dice", rounds, rtp, rounds * STAKE, payout, int(wins), {"over": over, "display_mult": mult})


def sim_keno(rounds: int, rtp: float, *, n_picks: int = 5) -> SimResult:
    n_picks = max(1, min(10, n_picks))
    row = KENO_TABLE[n_picks]
    weight = keno_pick_weight(rtp, n_picks)
    payout = wins = 0.0
    for _ in range(rounds):
        picks = set(random.sample(range(40), n_picks))
        drawn = draw_keno(random.Random(), picks, pick_weight=weight)
        hits = sum(1 for p in picks if p in drawn)
        mult = row[hits]
        if mult > 0:
            wins += 1
        payout += STAKE * mult
    return SimResult(
        "keno", rounds, rtp, rounds * STAKE, payout, int(wins),
        {"picks": n_picks, "pick_weight": weight, "draw_count": DRAW_COUNT},
    )


def sim_crash(rounds: int, rtp: float, *, auto_cashout: float = 2.0) -> SimResult:
    boost = crash_payout_boost(rtp)
    payout = wins = 0.0
    for _ in range(rounds):
        r = random.random()
        crash_point = crash_multiplier(r, rtp=rtp)
        if auto_cashout <= crash_point:
            payout += STAKE * auto_cashout * boost
            wins += 1
    return SimResult(
        "crash", rounds, rtp, rounds * STAKE, payout, int(wins),
        {"auto_cashout": auto_cashout, "payout_boost": boost},
    )


def sim_blackjack(rounds: int, rtp: float) -> SimResult:
    bias = bj_dealer_bias_rate(rtp)
    payout = wins = 0.0
    for _ in range(rounds):
        deck = new_shoe()
        player = draw(deck, 2)
        dealer = deal_initial_dealer(deck, dealer_bias_rate=bias)
        up_val = hand_value([dealer[0]])
        while hand_value(player) < _basic_stand_threshold(up_val) and not is_bust(player):
            player.extend(draw(deck, 1))
        if is_bust(player):
            outcome = "lose"
        else:
            dealer_final = play_dealer(deck, dealer)
            outcome = compare_hands(player, dealer_final)
        round_payout, _ = payout_for_outcome(STAKE, outcome)
        payout += round_payout
        if outcome in ("win", "blackjack"):
            wins += 1
    return SimResult("blackjack", rounds, rtp, rounds * STAKE, payout, int(wins), {"dealer_bias_rate": bias})


RUNNERS = {
    "limbo": sim_limbo,
    "dice": sim_dice,
    "keno": sim_keno,
    "crash": sim_crash,
    "blackjack": sim_blackjack,
}


def _prompt(text: str, default: str) -> str:
    raw = input(f"{text} [{default}]: ").strip()
    return raw or default


def _prompt_float(text: str, default: float, *, lo: float | None = None, hi: float | None = None) -> float:
    while True:
        raw = _prompt(text, str(default))
        try:
            val = float(raw)
        except ValueError:
            print("  Enter a number.")
            continue
        if lo is not None and val < lo:
            print(f"  Must be >= {lo}.")
            continue
        if hi is not None and val > hi:
            print(f"  Must be <= {hi}.")
            continue
        return val


def _prompt_int(text: str, default: int, *, lo: int = 1) -> int:
    while True:
        raw = _prompt(text, str(default))
        try:
            val = int(raw)
        except ValueError:
            print("  Enter a whole number.")
            continue
        if val < lo:
            print(f"  Must be >= {lo}.")
            continue
        return val


def _pick_game() -> str:
    print("\nGames:")
    for i, name in enumerate(GAMES, 1):
        print(f"  {i}. {name}")
    while True:
        raw = _prompt("Select game (number or name)", "1")
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(GAMES):
                return GAMES[idx - 1]
        if raw.lower() in GAMES:
            return raw.lower()
        print("  Invalid choice.")


def _game_kwargs(game: str, rtp: float) -> dict:
    if game == "limbo":
        return {"target": _prompt_float("Target multiplier", 2.0, lo=1.01)}
    if game == "dice":
        return {"over": _prompt_float("Roll over", 50.5, lo=0.01, hi=99.99)}
    if game == "keno":
        return {"n_picks": _prompt_int("Number of picks (1-10)", 5, lo=1)}
    if game == "crash":
        return {"auto_cashout": _prompt_float("Auto cashout multiplier", 2.0, lo=1.01)}
    return {}


def print_result(res: SimResult) -> None:
    print("\n" + "=" * 48)
    print(f"  Game:          {res.game}")
    print(f"  Rounds:        {res.rounds:,}")
    print(f"  Target RTP:    {res.rtp_target:.1%}")
    print(f"  Stake/round:   {STAKE}")
    for k, v in res.extra.items():
        if isinstance(v, float):
            print(f"  {k.replace('_', ' ').title():14} {v:.4f}")
        else:
            print(f"  {k.replace('_', ' ').title():14} {v}")
    print("-" * 48)
    print(f"  Total wagered: {res.total_wagered:,.2f}")
    print(f"  Total payout:  {res.total_payout:,.2f}")
    print(f"  Net (player):  {res.net:+,.2f}")
    print(f"  Actual RTP:    {res.rtp_actual:.2%}")
    print(f"  Win rate:      {res.win_rate:.2%}  ({res.wins:,} wins)")
    print(f"  Margin:        {(1 - res.rtp_actual):.2%}")
    print("=" * 48 + "\n")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Simulate casino game rounds.")
    p.add_argument("--game", choices=GAMES, help="Game to simulate")
    p.add_argument("--rtp", type=float, default=DEFAULT_RTP_PCT, help="Target return %% (default 80)")
    p.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS, help="Number of rounds")
    p.add_argument("--target", type=float, help="Limbo target multiplier")
    p.add_argument("--over", type=float, help="Dice roll-over threshold")
    p.add_argument("--picks", type=int, help="Keno number of picks (1-10)")
    p.add_argument("--cashout", type=float, help="Crash auto cashout multiplier")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    if args.game:
        game = args.game
        rtp_pct = args.rtp
        rounds = args.rounds
        kwargs: dict = {}
        if game == "limbo":
            kwargs["target"] = args.target if args.target is not None else 2.0
        elif game == "dice":
            kwargs["over"] = args.over if args.over is not None else 50.5
        elif game == "keno":
            kwargs["n_picks"] = args.picks if args.picks is not None else 5
        elif game == "crash":
            kwargs["auto_cashout"] = args.cashout if args.cashout is not None else 2.0
    else:
        print("Casino game simulator")
        game = _pick_game()
        rtp_pct = _prompt_float("Target RTP (%)", DEFAULT_RTP_PCT, lo=1, hi=99)
        rounds = _prompt_int("Rounds to play", DEFAULT_ROUNDS, lo=1)
        kwargs = _game_kwargs(game, rtp_pct / 100)

    rtp = rtp_pct / 100
    if game == "keno" and "n_picks" in kwargs:
        kwargs["n_picks"] = max(1, min(10, int(kwargs["n_picks"])))

    print(f"\nRunning {rounds:,} rounds of {game} at {rtp:.0%} RTP...")
    res = RUNNERS[game](rounds, rtp, **kwargs)
    print_result(res)


if __name__ == "__main__":
    main()
