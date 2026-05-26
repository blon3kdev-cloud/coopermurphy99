"""Dice2 — provably-fair rolls; fixed board per difficulty (90% RTP tuned)."""
from __future__ import annotations

import hashlib
import hmac

DICE2_TARGET_RTP = 0.90

DIFFICULTY_EASY = "easy"
DIFFICULTY_MEDIUM = "medium"
DIFFICULTY_HARD = "hard"
DIFFICULTIES = (DIFFICULTY_EASY, DIFFICULTY_MEDIUM, DIFFICULTY_HARD)
DEFAULT_DIFFICULTY = DIFFICULTY_MEDIUM

PATH_LEN = 12
GOLDEN_INDEX = 6

# 4×4 ring path (matches frontend PATH); index 0 = start, 6 = golden
PATH_COORDS: list[tuple[int, int]] = [
    (0, 0), (0, 1), (0, 2), (0, 3),
    (1, 3), (2, 3), (3, 3),
    (3, 2), (3, 1), (3, 0),
    (2, 0), (1, 0),
]

# Tuned for ~90% RTP with realistic play (mix of 1–2 rolls before cashout).
# Safe tiles are all >= 1.05x so a survived roll is never a hidden loss.
_DICE2_PRESETS: dict[str, dict] = {
    DIFFICULTY_EASY: {
        "golden_mult": 1.95,
        "deadly": frozenset({5, 7}),
        "mults": {
            1: 1.52,
            2: 1.07,
            3: 1.05,
            4: 1.05,
            8: 1.05,
            9: 1.05,
            10: 1.14,
            11: 1.07,
        },
    },
    DIFFICULTY_MEDIUM: {
        "golden_mult": 2.25,
        "deadly": frozenset({2, 5, 7}),
        "mults": {
            1: 1.61,
            3: 1.08,
            4: 1.05,
            8: 1.05,
            9: 1.05,
            10: 1.21,
            11: 1.13,
        },
    },
    DIFFICULTY_HARD: {
        "golden_mult": 2.55,
        "deadly": frozenset({5, 7, 9}),
        "mults": {
            1: 1.64,
            2: 1.16,
            3: 1.10,
            4: 1.05,
            8: 1.05,
            10: 1.23,
            11: 1.16,
        },
    },
}


def normalize_difficulty(raw: str | None) -> str:
    if not raw:
        return DEFAULT_DIFFICULTY
    key = str(raw).strip().lower()
    if key in _DICE2_PRESETS:
        return key
    return DEFAULT_DIFFICULTY


def build_board(*, difficulty: str = DEFAULT_DIFFICULTY) -> list[dict]:
    """Fixed layout for the chosen difficulty (seed only affects dice rolls)."""
    diff = normalize_difficulty(difficulty)
    preset = _DICE2_PRESETS[diff]
    deadly = preset["deadly"]
    golden_mult = float(preset["golden_mult"])
    mults: dict[int, float] = preset["mults"]

    tiles: list[dict] = []
    for i in range(PATH_LEN):
        if i == 0:
            tiles.append({"start": True})
        elif i in deadly:
            tiles.append({"deadly": True})
        elif i == GOLDEN_INDEX:
            tiles.append({"golden": True, "mult": golden_mult})
        else:
            tiles.append({"mult": float(mults[i])})
    return tiles


def roll_dice(seed: str, roll_index: int) -> tuple[int, int]:
    digest = hmac.new(
        seed.encode(),
        f"dice2:roll:{roll_index}".encode(),
        hashlib.sha256,
    ).digest()
    return (digest[0] % 6) + 1, (digest[1] % 6) + 1


def apply_roll(
    tiles: list[dict],
    path_pos: int,
    combined_mult: float,
    die_a: int,
    die_b: int,
) -> tuple[int, float, bool, float | None]:
    """Returns ``(new_pos, new_mult, busted, tile_mult_or_none)``."""
    steps = die_a + die_b
    new_pos = (path_pos + steps) % PATH_LEN
    meta = tiles[new_pos]
    if meta.get("deadly"):
        return new_pos, combined_mult, True, None
    tile_mult = meta.get("mult")
    new_mult = combined_mult
    if tile_mult is not None and new_pos != 0:
        new_mult = round(combined_mult * float(tile_mult), 2)
        # Never drop below 1x on a safe tile (avoids "survived but lost money").
        new_mult = max(1.0, new_mult)
    return new_pos, new_mult, False, tile_mult


def cashout_payout(stake: float, combined_mult: float) -> float:
    """Full stake × on-screen multiplier (no post-hoc RTP haircut)."""
    return round(stake * combined_mult, 2)
