"""Provably-fair casino RNG — Dice / Limbo / Keno / Blackjack.

Each round writes a `casino_rounds` audit row with the server-side seed.
"""
from __future__ import annotations

import hashlib
import secrets
from decimal import Decimal
from random import SystemRandom

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from pymongo import ReturnDocument
from typing import Literal

from ..blackjack_engine import (
    can_double_cards,
    can_split_cards,
    compare_hands,
    deal_initial_dealer,
    dealer_visible,
    draw,
    is_blackjack,
    is_bust,
    is_twenty_one,
    new_shoe,
    payout_for_outcome,
    play_dealer,
)
from ..casino_rtp import (
    BLITZ_UNIQUE_MAX,
    LEGACY_PAYOUT_EDGE,
    bj_dealer_bias_rate,
    blitz_multiplier,
    blitz_simulate,
    crash_multiplier,
    dice_roll_and_win,
    draw_keno,
    keno_pick_weight,
    resolve_rtp,
    seeded_pair,
)
from ..dice2_engine import (
    DEFAULT_DIFFICULTY,
    normalize_difficulty,
    apply_roll,
    build_board,
    cashout_payout,
    roll_dice,
)
from ..db import get_db, next_id, now
from ..rate_limit import rate_limit_request
from ..rewards_service import record_vip_activity
from ..security import get_current_user

router = APIRouter(prefix="/api/games", tags=["games"])


def _seeded_random() -> tuple[str, float]:
    """Returns ``(seed_hex, value_in_[0,1))`` — used by Limbo."""
    seed, r1, _ = seeded_pair()
    return seed, r1


async def _settle(user_id: int, game: str, stake: Decimal, payout: Decimal,
                  details: dict, seed: str) -> Decimal:
    db = get_db()
    updated = await db.users.find_one_and_update(
        {"id": user_id, "balance_pln": {"$gte": stake}},
        {"$inc": {"balance_pln": payout - stake}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="insufficient balance")
    await db.casino_rounds.insert_one(
        {
            "id": await next_id("casino_rounds"),
            "user_id": user_id,
            "game": game,
            "stake_pln": stake,
            "payout_pln": payout,
            "details": details,
            "server_seed": seed,
            "created_at": now(),
        }
    )
    await record_vip_activity(user_id, stake, payout)
    return updated["balance_pln"]


# ── Dice ─────────────────────────────────────────────────────────────────────

class DiceBody(BaseModel):
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    over: float = Field(gt=0, lt=100)


@router.post("/dice")
async def play_dice(
    request: Request,
    payload: DiceBody,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.dice", 60)
    rtp = resolve_rtp(user)
    win_chance = (100 - payload.over) / 100
    multiplier = round(LEGACY_PAYOUT_EDGE / win_chance, 4) if win_chance > 0 else 0
    seed, r1, r2 = seeded_pair()
    roll, won = dice_roll_and_win(payload.over, r1, r2, rtp=rtp)
    payout = (payload.stakePln * Decimal(str(multiplier))).quantize(Decimal("0.01")) if won else Decimal("0.00")

    new_bal = await _settle(
        user["id"], "dice", payload.stakePln, payout,
        {"over": payload.over, "roll": roll, "won": won}, seed,
    )
    return {"ok": True, "roll": roll, "won": won, "payout": float(payout), "balance": float(new_bal)}


# ── Limbo ────────────────────────────────────────────────────────────────────

class LimboBody(BaseModel):
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    target: float = Field(ge=1.01, le=1_000_000)


@router.post("/limbo")
async def play_limbo(
    request: Request,
    payload: LimboBody,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.limbo", 60)
    rtp = resolve_rtp(user)
    seed, r = _seeded_random()
    crash = crash_multiplier(r, rtp=rtp)
    won = crash >= payload.target
    payout = (payload.stakePln * Decimal(str(payload.target))).quantize(Decimal("0.01")) if won else Decimal("0.00")

    new_bal = await _settle(
        user["id"], "limbo", payload.stakePln, payout,
        {"target": payload.target, "crash": crash, "won": won}, seed,
    )
    return {"ok": True, "crash": crash, "won": won, "payout": float(payout), "balance": float(new_bal)}


# ── Keno ─────────────────────────────────────────────────────────────────────

CELL_COUNT = 40
DRAW_COUNT = 10
KENO_TABLE = {
    1:  [0, 3.5],
    2:  [0, 0, 15],
    3:  [0, 0, 0, 80],
    4:  [0, 0, 0, 12, 200],
    5:  [0, 0, 0, 4.5, 45, 450],
    6:  [0, 0, 0, 0, 6, 13, 450],
    7:  [0, 0, 0, 0, 3, 8, 13, 500],
    8:  [0, 0, 0, 0, 3, 6, 13, 40, 650],
    9:  [0, 0, 0, 0, 3, 8, 13, 40, 400, 800],
    10: [0, 0, 0, 0, 3.5, 8, 13, 40, 400, 650, 1000],
}


class KenoBody(BaseModel):
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    picks: list[int] = Field(min_length=1, max_length=10)


@router.post("/keno")
async def play_keno(
    request: Request,
    payload: KenoBody,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.keno", 60)
    rtp = resolve_rtp(user)
    picks = sorted({p for p in payload.picks if 0 <= p < CELL_COUNT})
    if not picks:
        raise HTTPException(status_code=400, detail="invalid picks")
    seed = secrets.token_hex(32)
    rng = SystemRandom(int(hashlib.sha256(seed.encode()).hexdigest(), 16))
    drawn = draw_keno(
        rng,
        set(picks),
        cell_count=CELL_COUNT,
        draw_count=DRAW_COUNT,
        pick_weight=keno_pick_weight(rtp, len(picks)),
    )
    hits = sum(1 for p in picks if p in drawn)
    mult = KENO_TABLE[len(picks)][hits]
    payout = (payload.stakePln * Decimal(str(mult))).quantize(Decimal("0.01"))

    new_bal = await _settle(
        user["id"], "keno", payload.stakePln, payout,
        {"picks": picks, "drawn": sorted(drawn), "hits": hits}, seed,
    )
    return {
        "ok": True, "drawn": sorted(drawn), "hits": hits,
        "multiplier": mult, "payout": float(payout), "balance": float(new_bal),
    }


# ── Blitz ────────────────────────────────────────────────────────────────────

class BlitzBody(BaseModel):
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    uniqueCards: int = Field(ge=5, le=BLITZ_UNIQUE_MAX)


@router.post("/blitz")
async def play_blitz(
    request: Request,
    payload: BlitzBody,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.blitz", 60)
    rtp = resolve_rtp(user)
    unique = int(payload.uniqueCards)
    mult = blitz_multiplier(unique, rtp=rtp)
    seed = secrets.token_hex(32)
    won, picks = blitz_simulate(unique, seed, rtp=rtp)
    payout = (
        (payload.stakePln * Decimal(str(mult))).quantize(Decimal("0.01"))
        if won
        else Decimal("0.00")
    )
    new_bal = await _settle(
        user["id"],
        "blitz",
        payload.stakePln,
        payout,
        {"uniqueCards": unique, "picks": picks, "won": won, "multiplier": mult},
        seed,
    )
    return {
        "ok": True,
        "won": won,
        "picks": picks,
        "uniqueCards": unique,
        "multiplier": mult,
        "payout": float(payout),
        "balance": float(new_bal),
    }


# ── Dice2 ───────────────────────────────────────────────────────────────────

class Dice2StartBody(BaseModel):
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)
    difficulty: str = DEFAULT_DIFFICULTY


async def _get_dice2_session(user_id: int) -> dict | None:
    return await get_db().dice2_sessions.find_one(
        {"user_id": user_id, "status": "playing"},
    )


def _dice2_projected_payout(session: dict) -> float:
    return cashout_payout(
        float(session["stake_pln"]),
        float(session["combined_mult"]),
    )


def _dice2_payload(session: dict, balance: float) -> dict:
    return {
        "ok": True,
        "sessionId": session["id"],
        "difficulty": session.get("difficulty", DEFAULT_DIFFICULTY),
        "tiles": session["tiles"],
        "pathPos": int(session["path_pos"]),
        "combinedMult": float(session["combined_mult"]),
        "hasRolled": bool(session.get("has_rolled")),
        "projectedPayout": _dice2_projected_payout(session),
        "balance": balance,
    }


@router.post("/dice2/start")
async def dice2_start(
    request: Request,
    payload: Dice2StartBody,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.dice2", 120)
    db = get_db()
    difficulty = normalize_difficulty(payload.difficulty)
    existing = await _get_dice2_session(user["id"])
    if existing:
        user_doc = await db.users.find_one({"id": user["id"]})
        bal = float(user_doc["balance_pln"]) if user_doc else 0.0
        return {"ok": True, "resumed": True, **_dice2_payload(existing, bal)}

    stake = payload.stakePln
    balance_after_lock = await _lock_stake(user["id"], stake)
    seed = secrets.token_hex(32)
    session_id = await next_id("dice2_sessions")
    session_doc = {
        "id": session_id,
        "user_id": user["id"],
        "stake_pln": stake,
        "status": "playing",
        "difficulty": difficulty,
        "server_seed": seed,
        "tiles": build_board(difficulty=difficulty),
        "path_pos": 0,
        "combined_mult": 1.0,
        "roll_count": 0,
        "has_rolled": False,
        "created_at": now(),
    }
    await db.dice2_sessions.insert_one(session_doc)
    return {
        "ok": True,
        "resumed": False,
        **_dice2_payload(session_doc, float(balance_after_lock)),
    }


@router.post("/dice2/roll")
async def dice2_roll(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.dice2", 120)
    session = await _get_dice2_session(user["id"])
    if not session:
        raise HTTPException(status_code=400, detail="no active dice2 round")

    seed = session["server_seed"]
    roll_index = int(session.get("roll_count", 0))
    die_a, die_b = roll_dice(seed, roll_index)
    tiles = session["tiles"]
    path_pos = int(session["path_pos"])
    combined_mult = float(session["combined_mult"])

    new_pos, new_mult, busted, tile_mult = apply_roll(
        tiles,
        path_pos,
        combined_mult,
        die_a,
        die_b,
    )

    session["path_pos"] = new_pos
    session["combined_mult"] = new_mult
    session["roll_count"] = roll_index + 1
    session["has_rolled"] = True

    body: dict = {
        "ok": True,
        "sessionId": session["id"],
        "dieA": die_a,
        "dieB": die_b,
        "pathPos": new_pos,
        "combinedMult": new_mult,
        "busted": busted,
        "tileMult": tile_mult,
        "hasRolled": True,
    }

    if busted:
        new_bal = await _finish_dice2(
            user["id"],
            session,
            payout=Decimal("0.00"),
            details={
                "dieA": die_a,
                "dieB": die_b,
                "pathPos": new_pos,
                "busted": True,
                "combinedMult": combined_mult,
            },
        )
        body["payout"] = 0.0
        body["balance"] = float(new_bal)
        return body

    await get_db().dice2_sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "path_pos": new_pos,
                "combined_mult": new_mult,
                "roll_count": roll_index + 1,
                "has_rolled": True,
            },
        },
    )
    user_doc = await get_db().users.find_one({"id": user["id"]})
    body["balance"] = float(user_doc["balance_pln"]) if user_doc else 0.0
    body["projectedPayout"] = _dice2_projected_payout(session)
    return body


@router.post("/dice2/cashout")
async def dice2_cashout(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.dice2", 120)
    session = await _get_dice2_session(user["id"])
    if not session:
        raise HTTPException(status_code=400, detail="no active dice2 round")
    if not session.get("has_rolled"):
        raise HTTPException(status_code=400, detail="roll before cashout")

    stake_f = float(session["stake_pln"])
    combined_mult = float(session["combined_mult"])
    payout_f = cashout_payout(stake_f, combined_mult)
    payout = Decimal(str(payout_f)).quantize(Decimal("0.01"))

    new_bal = await _finish_dice2(
        user["id"],
        session,
        payout=payout,
        details={
            "pathPos": int(session["path_pos"]),
            "combinedMult": combined_mult,
            "cashout": True,
        },
    )
    return {
        "ok": True,
        "combinedMult": combined_mult,
        "payout": float(payout),
        "balance": float(new_bal),
    }


async def _finish_dice2(
    user_id: int,
    session: dict,
    *,
    payout: Decimal,
    details: dict,
) -> Decimal:
    db = get_db()
    stake = session["stake_pln"]
    updated = await db.users.find_one_and_update(
        {"id": user_id},
        {"$inc": {"balance_pln": payout}},
        return_document=ReturnDocument.AFTER,
    )
    if session.get("_id") is not None:
        await db.dice2_sessions.delete_one({"_id": session["_id"]})
    seed = session.get("server_seed", "")
    await db.casino_rounds.insert_one(
        {
            "id": await next_id("casino_rounds"),
            "user_id": user_id,
            "game": "dice2",
            "stake_pln": stake,
            "payout_pln": payout,
            "details": details,
            "server_seed": seed,
            "created_at": now(),
        },
    )
    await record_vip_activity(user_id, stake, payout)
    return updated["balance_pln"]


# ── Blackjack ────────────────────────────────────────────────────────────────

class BlackjackStartBody(BaseModel):
    stakePln: Decimal = Field(gt=0, max_digits=20, decimal_places=2)


async def _get_blackjack_session(user_id: int) -> dict | None:
    return await get_db().blackjack_sessions.find_one(
        {"user_id": user_id, "status": "playing"},
    )


def _bj_session_invalid_reason(session: dict) -> str | None:
    """Return a reason code when the persisted round cannot be played safely."""
    try:
        deck = session.get("deck")
        dealer = session.get("dealer")
        if not isinstance(deck, list) or not isinstance(dealer, list):
            return "missing_deck_or_dealer"
        if len(dealer) < 2:
            return "dealer_hand_too_short"

        hands = _bj_hands(session)
        if not hands or any(len(h) < 1 for h in hands):
            return "empty_player_hand"

        active = _bj_active_hand(session)
        if active < 0 or active >= len(hands):
            return "active_hand_out_of_range"

        doubled = _bj_doubled(session)
        if len(doubled) != len(hands):
            return "doubled_flags_mismatch"

        hand_stakes = _bj_hand_stakes(session)
        if len(hand_stakes) != len(hands):
            return "hand_stakes_mismatch"

        split = bool(session.get("split"))
        if split and len(hands) != 2:
            return "split_state_inconsistent"
        if not split and len(hands) != 1:
            return "hand_count_invalid"

        stake = float(session.get("stake_pln", 0))
        if stake <= 0:
            return "invalid_stake"

        if _bj_unit_stake(session) <= 0:
            return "invalid_unit_stake"

        hand = hands[active]
        if is_bust(hand):
            return "active_hand_bust"

        if all(
            doubled[i] or is_bust(h) or is_twenty_one(h)
            for i, h in enumerate(hands)
        ):
            return "all_hands_resolved"

        opts = _bj_play_options(session)
        if is_twenty_one(hand) and opts["can_hit"]:
            return "can_hit_on_twenty_one"

        if doubled[active] and len(hand) not in (2, 3):
            return "doubled_hand_invalid_size"
    except (IndexError, KeyError, TypeError, ValueError):
        return "session_parse_error"
    return None


async def _abandon_blackjack_session(
    user_id: int,
    session: dict,
    *,
    reason: str,
) -> float:
    """Delete a corrupt round and refund the locked stake."""
    db = get_db()
    stake = Decimal(str(session["stake_pln"])).quantize(Decimal("0.01"))
    if session.get("_id") is not None:
        await db.blackjack_sessions.delete_one({"_id": session["_id"]})
    updated = await db.users.find_one_and_update(
        {"id": user_id},
        {"$inc": {"balance_pln": stake}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=500, detail="user not found")
    seed = session.get("server_seed", "")
    await db.casino_rounds.insert_one(
        {
            "id": await next_id("casino_rounds"),
            "user_id": user_id,
            "game": "blackjack",
            "stake_pln": stake,
            "payout_pln": stake,
            "details": {"void": True, "reason": reason, "outcome": "void"},
            "server_seed": seed,
            "created_at": now(),
        },
    )
    await record_vip_activity(user_id, stake, stake)
    return float(updated["balance_pln"])


async def _ensure_valid_blackjack_session(user_id: int, session: dict) -> dict | None:
    """Recover stuck rounds or void corrupt sessions. Returns None when cleared."""
    reason = _bj_session_invalid_reason(session)
    if reason is None:
        return session

    hands = _bj_hands(session)
    dealer = list(session["dealer"])
    deck = list(session["deck"])

    if reason == "active_hand_bust":
        await _advance_or_complete(
            user_id,
            session,
            hands,
            dealer,
            deck,
            details_extra={"recovered": True, "reason": reason},
        )
        return None

    if reason == "all_hands_resolved":
        await _complete_multi_hand_round(
            user_id,
            session,
            hands,
            dealer,
            deck,
            details_extra={"recovered": True, "reason": reason},
        )
        return None

    await _abandon_blackjack_session(user_id, session, reason=reason)
    return None


async def _load_blackjack_session(user_id: int) -> dict | None:
    session = await _get_blackjack_session(user_id)
    if not session:
        return None
    return await _ensure_valid_blackjack_session(user_id, session)


async def _lock_stake(user_id: int, stake: Decimal) -> Decimal:
    updated = await get_db().users.find_one_and_update(
        {"id": user_id, "balance_pln": {"$gte": stake}},
        {"$inc": {"balance_pln": -stake}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(status_code=400, detail="insufficient balance")
    return updated["balance_pln"]


async def _finish_blackjack(
    user_id: int,
    session: dict,
    *,
    outcome: str,
    payout: Decimal,
    details: dict,
) -> tuple[Decimal, float, float]:
    db = get_db()
    stake = session["stake_pln"]
    updated = await db.users.find_one_and_update(
        {"id": user_id},
        {"$inc": {"balance_pln": payout}},
        return_document=ReturnDocument.AFTER,
    )
    if session.get("_id") is not None:
        await db.blackjack_sessions.delete_one({"_id": session["_id"]})
    seed = session.get("server_seed", "")
    await db.casino_rounds.insert_one(
        {
            "id": await next_id("casino_rounds"),
            "user_id": user_id,
            "game": "blackjack",
            "stake_pln": stake,
            "payout_pln": payout,
            "details": {**details, "outcome": outcome},
            "server_seed": seed,
            "created_at": now(),
        }
    )
    await record_vip_activity(user_id, stake, payout)
    mult = float(payout / stake) if stake > 0 and payout > 0 else 0.0
    return updated["balance_pln"], float(payout), mult


def _bj_hands(session: dict) -> list[list]:
    if "hands" in session:
        return [list(h) for h in session["hands"]]
    return [list(session["player"])]


def _sync_bj_session_hands(session: dict, hands: list[list]) -> None:
    """Keep in-memory session aligned with mutations before building API payloads."""
    session["hands"] = hands
    active = _bj_active_hand(session)
    session["player"] = list(hands[active])


def _bj_active_hand(session: dict) -> int:
    return int(session.get("active_hand", 0))


def _bj_hand_stakes(session: dict) -> list[float]:
    if "hand_stakes" in session:
        return [float(s) for s in session["hand_stakes"]]
    return [float(session["stake_pln"])]


def _bj_unit_stake(session: dict) -> float:
    return float(session.get("unit_stake", session["stake_pln"]))


def _bj_doubled(session: dict) -> list[bool]:
    hands = _bj_hands(session)
    flags = session.get("doubled")
    if flags is None:
        return [False] * len(hands)
    return [bool(x) for x in flags]


def _bj_play_options(session: dict) -> dict:
    hands = _bj_hands(session)
    active = _bj_active_hand(session)
    hand = hands[active]
    doubled = _bj_doubled(session)
    split = bool(session.get("split"))
    return {
        "can_hit": not doubled[active] and not is_twenty_one(hand),
        "can_double": can_double_cards(hand, already_doubled=doubled[active]),
        "can_split": (
            not split
            and len(hands) == 1
            and can_split_cards(hand)
        ),
    }


def _playing_session_payload(session: dict, balance: float) -> dict:
    hands = _bj_hands(session)
    active = _bj_active_hand(session)
    opts = _bj_play_options(session)
    return _bj_response(
        phase="playing",
        player=hands[active],
        dealer=dealer_visible(session["dealer"], reveal=False),
        balance=balance,
        session_id=session["id"],
        hands=hands if session.get("split") else None,
        active_hand=active,
        split=bool(session.get("split")),
        doubled=_bj_doubled(session),
        unit_stake_pln=_bj_unit_stake(session),
        stake_pln=float(session["stake_pln"]),
        **opts,
    )


def _all_player_hands_bust(hands: list[list]) -> bool:
    return bool(hands) and all(is_bust(h) for h in hands)


def _aggregate_outcome(total_stake: float, total_payout: Decimal) -> str:
    paid = float(total_payout)
    if paid <= 0:
        return "lose"
    if abs(paid - total_stake) < 0.005:
        return "push"
    if paid > total_stake:
        return "win"
    return "lose"


async def _complete_multi_hand_round(
    user_id: int,
    session: dict,
    hands: list[list],
    dealer: list,
    deck: list,
    *,
    details_extra: dict | None = None,
) -> dict:
    if _all_player_hands_bust(hands):
        dealer_final = list(dealer)
    else:
        dealer_final = play_dealer(deck, list(dealer))
    hand_stakes = _bj_hand_stakes(session)
    total_payout = Decimal("0.00")
    hand_outcomes: list[str] = []
    for hand, stake in zip(hands, hand_stakes):
        outcome = compare_hands(hand, dealer_final)
        hand_outcomes.append(outcome)
        pay, _ = payout_for_outcome(stake, outcome)
        total_payout += Decimal(str(pay)).quantize(Decimal("0.01"))

    total_stake = float(session["stake_pln"])
    agg = _aggregate_outcome(total_stake, total_payout)
    details: dict = {
        "dealer": dealer_final,
        "handOutcomes": hand_outcomes,
    }
    if len(hands) == 1:
        details["player"] = hands[0]
    else:
        details["hands"] = hands
        details["split"] = True
    if details_extra:
        details.update(details_extra)

    bal, paid, mult = await _finish_blackjack(
        user_id,
        session,
        outcome=agg,
        payout=total_payout,
        details=details,
    )
    return _bj_response(
        phase="finished",
        player=hands[-1],
        dealer=dealer_visible(dealer_final, reveal=True),
        balance=float(bal),
        session_id=session["id"],
        outcome=agg,
        payout=paid,
        multiplier=mult,
        hands=hands,
        hand_outcomes=hand_outcomes,
        split=len(hands) > 1,
        stake_pln=total_stake,
        unit_stake_pln=_bj_unit_stake(session),
    )


async def _advance_or_complete(
    user_id: int,
    session: dict,
    hands: list[list],
    dealer: list,
    deck: list,
    *,
    details_extra: dict | None = None,
) -> dict:
    active = _bj_active_hand(session)
    # Split: play right hand (index 1) first, then left (index 0), then dealer.
    if session.get("split") and len(hands) == 2 and active > 0:
        next_hand = active - 1
    elif active + 1 < len(hands):
        next_hand = active + 1
    else:
        next_hand = None

    if next_hand is not None:
        session["active_hand"] = next_hand
        _sync_bj_session_hands(session, hands)
        await get_db().blackjack_sessions.update_one(
            {"_id": session["_id"]},
            {
                "$set": {
                    "hands": hands,
                    "active_hand": session["active_hand"],
                    "dealer": dealer,
                    "deck": deck,
                },
            },
        )
        user_doc = await get_db().users.find_one({"id": user_id})
        bal = float(user_doc["balance_pln"]) if user_doc else 0.0
        return _playing_session_payload(session, bal)

    _sync_bj_session_hands(session, hands)
    return await _complete_multi_hand_round(
        user_id,
        session,
        hands,
        dealer,
        deck,
        details_extra=details_extra,
    )


def _bj_response(
    *,
    phase: str,
    player: list,
    dealer: list,
    balance: float,
    session_id: int | None = None,
    outcome: str | None = None,
    payout: float | None = None,
    multiplier: float | None = None,
    hands: list[list] | None = None,
    active_hand: int | None = None,
    split: bool | None = None,
    doubled: list[bool] | None = None,
    can_hit: bool | None = None,
    can_double: bool | None = None,
    can_split: bool | None = None,
    unit_stake_pln: float | None = None,
    stake_pln: float | None = None,
    hand_outcomes: list[str] | None = None,
) -> dict:
    body: dict = {
        "ok": True,
        "phase": phase,
        "player": player,
        "dealer": dealer,
        "balance": balance,
    }
    if session_id is not None:
        body["sessionId"] = session_id
    if outcome is not None:
        body["outcome"] = outcome
    if payout is not None:
        body["payout"] = payout
    if multiplier is not None:
        body["multiplier"] = multiplier
    if hands is not None:
        body["hands"] = hands
    if active_hand is not None:
        body["activeHand"] = active_hand
    if split is not None:
        body["split"] = split
    if doubled is not None:
        body["doubled"] = doubled
    if can_hit is not None:
        body["canHit"] = can_hit
    if can_double is not None:
        body["canDouble"] = can_double
    if can_split is not None:
        body["canSplit"] = can_split
    if unit_stake_pln is not None:
        body["unitStakePln"] = unit_stake_pln
    if stake_pln is not None:
        body["stakePln"] = stake_pln
    if hand_outcomes is not None:
        body["handOutcomes"] = hand_outcomes
    return body


@router.get("/blackjack/active")
async def blackjack_active(
    user: dict = Depends(get_current_user),
) -> dict:
    had_session = await _get_blackjack_session(user["id"]) is not None
    session = await _load_blackjack_session(user["id"])
    user_doc = await get_db().users.find_one({"id": user["id"]})
    bal = float(user_doc["balance_pln"]) if user_doc else 0.0
    if not session:
        body: dict = {"ok": True, "active": False, "balance": bal}
        if had_session:
            body["reset"] = True
        return body
    return {
        "ok": True,
        "active": True,
        "stakePln": float(session["stake_pln"]),
        **_playing_session_payload(session, bal),
    }


@router.post("/blackjack/reset")
async def blackjack_reset(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    """Clear an invalid or stuck blackjack round (refund or auto-settle)."""
    await rate_limit_request(request, "games.blackjack", 120)
    had_session = await _get_blackjack_session(user["id"]) is not None
    session = await _load_blackjack_session(user["id"])
    user_doc = await get_db().users.find_one({"id": user["id"]})
    bal = float(user_doc["balance_pln"]) if user_doc else 0.0
    if not session:
        return {"ok": True, "active": False, "reset": had_session, "balance": bal}
    return {
        "ok": True,
        "active": True,
        "reset": False,
        "stakePln": float(session["stake_pln"]),
        **_playing_session_payload(session, bal),
    }


@router.post("/blackjack/start")
async def blackjack_start(
    request: Request,
    payload: BlackjackStartBody,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.blackjack", 120)
    db = get_db()
    existing = await _load_blackjack_session(user["id"])
    if existing:
        user_doc = await db.users.find_one({"id": user["id"]})
        bal = float(user_doc["balance_pln"]) if user_doc else 0.0
        return {
            "ok": True,
            "resumed": True,
            "stakePln": float(existing["stake_pln"]),
            **_playing_session_payload(existing, bal),
        }

    stake = payload.stakePln
    balance_after_lock = await _lock_stake(user["id"], stake)

    rtp = resolve_rtp(user)
    deck = new_shoe()
    seed = secrets.token_hex(32)
    player = draw(deck, 2)
    dealer = deal_initial_dealer(deck, dealer_bias_rate=bj_dealer_bias_rate(rtp))

    session_id = await next_id("blackjack_sessions")
    stake_f = float(stake)
    session_doc = {
        "id": session_id,
        "user_id": user["id"],
        "stake_pln": stake,
        "unit_stake": stake,
        "hand_stakes": [stake_f],
        "hands": [player],
        "active_hand": 0,
        "split": False,
        "doubled": [False],
        "deck": deck,
        "player": player,
        "dealer": dealer,
        "status": "playing",
        "server_seed": seed,
        "created_at": now(),
    }

    # Natural blackjack — settle immediately (no persisted session).
    if is_blackjack(player) or is_blackjack(dealer):
        outcome = compare_hands(player, dealer)
        payout_amt = Decimal(str(payout_for_outcome(float(stake), outcome)[0])).quantize(
            Decimal("0.01"),
        )
        bal, paid, mult = await _finish_blackjack(
            user["id"],
            session_doc,
            outcome=outcome,
            payout=payout_amt,
            details={"player": player, "dealer": dealer, "natural": True},
        )
        return _bj_response(
            phase="finished",
            player=player,
            dealer=dealer_visible(dealer, reveal=True),
            balance=float(bal),
            session_id=session_id,
            outcome=outcome,
            payout=paid,
            multiplier=mult,
            hands=[player],
            hand_outcomes=[outcome],
            split=False,
        )

    await db.blackjack_sessions.insert_one(session_doc)
    return {
        "ok": True,
        "resumed": False,
        "stakePln": float(stake),
        **_playing_session_payload(session_doc, float(balance_after_lock)),
    }


@router.post("/blackjack/hit")
async def blackjack_hit(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.blackjack", 120)
    session = await _load_blackjack_session(user["id"])
    if not session:
        raise HTTPException(status_code=400, detail="no active blackjack round")

    deck: list = session["deck"]
    dealer: list = list(session["dealer"])
    hands = _bj_hands(session)
    active = _bj_active_hand(session)
    doubled = _bj_doubled(session)
    if doubled[active]:
        raise HTTPException(status_code=400, detail="cannot hit after double")

    hand = list(hands[active])
    if is_twenty_one(hand):
        raise HTTPException(status_code=400, detail="hand is already 21")

    hand.extend(draw(deck, 1))
    hands[active] = hand
    _sync_bj_session_hands(session, hands)

    if is_bust(hand):
        return await _advance_or_complete(
            user["id"],
            session,
            hands,
            dealer,
            deck,
            details_extra={"bust": True, "bustHand": active},
        )

    if is_twenty_one(hand):
        return await _advance_or_complete(
            user["id"],
            session,
            hands,
            dealer,
            deck,
            details_extra={"auto_stood": True},
        )

    await get_db().blackjack_sessions.update_one(
        {"_id": session["_id"]},
        {"$set": {"hands": hands, "player": hand, "deck": deck}},
    )
    user_doc = await get_db().users.find_one({"id": user["id"]})
    bal = float(user_doc["balance_pln"]) if user_doc else 0.0
    return _playing_session_payload(session, bal)


@router.post("/blackjack/stand")
async def blackjack_stand(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.blackjack", 120)
    session = await _load_blackjack_session(user["id"])
    if not session:
        raise HTTPException(status_code=400, detail="no active blackjack round")

    deck: list = session["deck"]
    dealer: list = list(session["dealer"])
    hands = _bj_hands(session)
    return await _advance_or_complete(user["id"], session, hands, dealer, deck)


@router.post("/blackjack/double")
async def blackjack_double(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.blackjack", 120)
    session = await _load_blackjack_session(user["id"])
    if not session:
        raise HTTPException(status_code=400, detail="no active blackjack round")

    hands = _bj_hands(session)
    active = _bj_active_hand(session)
    hand = list(hands[active])
    doubled = _bj_doubled(session)
    if not can_double_cards(hand, already_doubled=doubled[active]):
        raise HTTPException(status_code=400, detail="double not allowed")

    unit = Decimal(str(_bj_unit_stake(session))).quantize(Decimal("0.01"))
    await _lock_stake(user["id"], unit)

    hand_stakes = _bj_hand_stakes(session)
    hand_stakes[active] += float(unit)
    doubled[active] = True
    total_stake = Decimal(str(session["stake_pln"])) + unit
    session["stake_pln"] = total_stake.quantize(Decimal("0.01"))
    session["hand_stakes"] = hand_stakes
    session["doubled"] = doubled

    deck: list = session["deck"]
    dealer: list = list(session["dealer"])
    hand.extend(draw(deck, 1))
    hands[active] = hand
    _sync_bj_session_hands(session, hands)

    await get_db().blackjack_sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "hands": hands,
                "player": hand,
                "deck": deck,
                "hand_stakes": hand_stakes,
                "doubled": doubled,
                "stake_pln": session["stake_pln"],
            },
        },
    )

    return await _advance_or_complete(
        user["id"],
        session,
        hands,
        dealer,
        deck,
        details_extra={"doubled": True, "doubleHand": active},
    )


@router.post("/blackjack/split")
async def blackjack_split(
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict:
    await rate_limit_request(request, "games.blackjack", 120)
    session = await _load_blackjack_session(user["id"])
    if not session:
        raise HTTPException(status_code=400, detail="no active blackjack round")

    if session.get("split"):
        raise HTTPException(status_code=400, detail="already split")

    hands = _bj_hands(session)
    if len(hands) != 1:
        raise HTTPException(status_code=400, detail="split not allowed")

    hand = list(hands[0])
    if not can_split_cards(hand):
        raise HTTPException(status_code=400, detail="split not allowed")

    unit = Decimal(str(_bj_unit_stake(session))).quantize(Decimal("0.01"))
    await _lock_stake(user["id"], unit)

    c0, c1 = hand[0], hand[1]
    deck: list = session["deck"]
    dealer: list = list(session["dealer"])
    new_hands = [[c0], [c1]]
    new_hands[0].extend(draw(deck, 1))
    new_hands[1].extend(draw(deck, 1))

    unit_f = float(unit)
    total_stake = Decimal(str(session["stake_pln"])) + unit
    session["stake_pln"] = total_stake.quantize(Decimal("0.01"))
    session["hands"] = new_hands
    session["hand_stakes"] = [unit_f, unit_f]
    session["split"] = True
    session["active_hand"] = 1
    session["doubled"] = [False, False]
    session["player"] = new_hands[1]

    await get_db().blackjack_sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "hands": new_hands,
                "player": new_hands[1],
                "deck": deck,
                "hand_stakes": session["hand_stakes"],
                "split": True,
                "active_hand": 1,
                "doubled": [False, False],
                "stake_pln": session["stake_pln"],
            },
        },
    )

    user_doc = await get_db().users.find_one({"id": user["id"]})
    bal = float(user_doc["balance_pln"]) if user_doc else 0.0
    return _playing_session_payload(session, bal)
