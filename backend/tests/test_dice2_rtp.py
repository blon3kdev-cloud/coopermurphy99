"""Monte Carlo RTP checks for Dice2 difficulties."""
from __future__ import annotations

from app.dice2_engine import (
    DICE2_TARGET_RTP,
    DIFFICULTIES,
    GOLDEN_INDEX,
    PATH_LEN,
    apply_roll,
    build_board,
    cashout_payout,
    roll_dice,
)


def _simulate_round(
    seed: str,
    difficulty: str,
    *,
    cash_after_safe: int = 1,
) -> float:
    tiles = build_board(difficulty=difficulty)
    path_pos = 0
    combined_mult = 1.0
    roll_index = 0
    safe_hits = 0
    stake = 1.0

    while roll_index < 40:
        die_a, die_b = roll_dice(seed, roll_index)
        path_pos, combined_mult, busted, _ = apply_roll(
            tiles,
            path_pos,
            combined_mult,
            die_a,
            die_b,
        )
        roll_index += 1
        if busted:
            return 0.0
        safe_hits += 1
        if safe_hits >= cash_after_safe:
            return cashout_payout(stake, combined_mult)
    return cashout_payout(stake, combined_mult)


def test_cashout_pays_full_multiplier():
    assert cashout_payout(10.0, 1.41) == 14.1


def test_dice2_board_layout_per_difficulty():
    for difficulty in DIFFICULTIES:
        tiles = build_board(difficulty=difficulty)
        assert len(tiles) == PATH_LEN
        assert tiles[0].get("start")
        deadly = sum(1 for t in tiles[1:] if t.get("deadly"))
        assert deadly >= 2
        golden = [t for t in tiles if t.get("golden")]
        assert len(golden) == 1
        assert golden[0]["mult"] == max(
            t["mult"] for t in tiles if t.get("mult") is not None
        )
        assert tiles[GOLDEN_INDEX].get("golden")
        assert tiles[GOLDEN_INDEX - 1].get("deadly")
        assert tiles[GOLDEN_INDEX + 1].get("deadly")
        for t in tiles:
            if t.get("mult") is not None and not t.get("golden"):
                assert t["mult"] >= 1.0, f"{difficulty} safe tile below 1x"


def test_dice2_rtp_near_target_all_difficulties():
    trials = 60_000
    for difficulty in DIFFICULTIES:
        total = sum(
            _simulate_round(f"{difficulty}-seed-{i}", difficulty, cash_after_safe=1)
            for i in range(trials)
        )
        measured = total / trials
        lo = DICE2_TARGET_RTP - 0.03
        hi = DICE2_TARGET_RTP + 0.03
        assert lo <= measured <= hi, (
            f"{difficulty} RTP {measured:.4f} outside {lo:.0%}–{hi:.0%}"
        )


def test_fair_dice_average():
    """Provably-fair rolls are uniform — long-run sum ≈ 7."""
    trials = 20_000
    total = 0
    for i in range(trials):
        a, b = roll_dice(f"fair-{i}", 0)
        total += a + b
    avg = total / trials
    assert 6.85 <= avg <= 7.15, f"avg dice sum {avg:.3f} not near 7"
