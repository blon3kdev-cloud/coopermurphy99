"""Blackjack shoe, hand evaluation, and dealer play."""
from __future__ import annotations

import secrets
from typing import Literal

SUITS = ("clubs", "diamonds", "hearts", "spades")
RANKS = (
    "ace", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "jack", "queen", "king",
)
Card = dict[str, str]
Deck = list[Card]

RANK_VALUES = {
    "ace": 11,
    "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "jack": 10, "queen": 10, "king": 10,
}

from .casino_rtp import BJ_DEALER_INIT_BIAS_RATE

DECKS = 6
BIAS_LOOKAHEAD = 8


def new_shoe() -> Deck:
    deck: Deck = [
        {"suit": suit, "rank": rank}
        for _ in range(DECKS)
        for suit in SUITS
        for rank in RANKS
    ]
    secrets.SystemRandom().shuffle(deck)
    return deck


def draw(deck: Deck, n: int = 1) -> list[Card]:
    if len(deck) < n:
        deck.extend(new_shoe())
    out = [deck.pop() for _ in range(n)]
    return out


def draw_biased(
    deck: Deck,
    hand: list[Card],
    *,
    favor: Literal["player", "dealer"],
    n: int = 1,
) -> list[Card]:
    """Deal from shoe top (pop end) with dealer-favorable card choice."""
    out: list[Card] = []
    for _ in range(n):
        if len(deck) < 1:
            deck.extend(new_shoe())
        window = min(BIAS_LOOKAHEAD, len(deck))
        start = len(deck) - window
        best_i = start
        trial_hand = hand + out
        best_val = hand_value(trial_hand + [deck[best_i]])
        for i in range(start, len(deck)):
            val = hand_value(trial_hand + [deck[i]])
            if favor == "player":
                if val < best_val:
                    best_val, best_i = val, i
            elif val > best_val:
                best_val, best_i = val, i
        out.append(deck.pop(best_i))
    return out


def hand_value(cards: list[Card]) -> int:
    total = 0
    aces = 0
    for card in cards:
        rank = card["rank"]
        if rank == "ace":
            aces += 1
            total += 11
        else:
            total += RANK_VALUES[rank]
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def is_blackjack(cards: list[Card]) -> bool:
    return len(cards) == 2 and hand_value(cards) == 21


def is_bust(cards: list[Card]) -> bool:
    return hand_value(cards) > 21


def is_twenty_one(cards: list[Card]) -> bool:
    """Hard/soft 21 on current hand (not bust). Natural blackjack uses ``is_blackjack``."""
    return not is_bust(cards) and hand_value(cards) == 21


def dealer_should_hit(cards: list[Card]) -> bool:
    return hand_value(cards) < 17


def deal_initial_dealer(
    deck: Deck,
    *,
    dealer_bias_rate: float | None = None,
) -> list[Card]:
    """Initial dealer hand (optional bias rate)."""
    rate = BJ_DEALER_INIT_BIAS_RATE if dealer_bias_rate is None else dealer_bias_rate
    if secrets.SystemRandom().random() < rate:
        return draw_biased(deck, [], favor="dealer", n=2)
    return draw(deck, 2)


def play_dealer(deck: Deck, dealer: list[Card]) -> list[Card]:
    hand = list(dealer)
    while dealer_should_hit(hand):
        hand.extend(draw(deck, 1))
    return hand


Outcome = Literal["win", "lose", "push", "blackjack"]


def compare_hands(player: list[Card], dealer: list[Card]) -> Outcome:
    p_val = hand_value(player)
    d_val = hand_value(dealer)
    p_bj = is_blackjack(player)
    d_bj = is_blackjack(dealer)

    if p_bj and d_bj:
        return "push"
    if p_bj:
        return "blackjack"
    if d_bj:
        return "lose"
    if p_val > 21:
        return "lose"
    if d_val > 21:
        return "win"
    if p_val > d_val:
        return "win"
    if p_val < d_val:
        return "lose"
    return "push"


def payout_for_outcome(stake: float, outcome: Outcome) -> tuple[float, float]:
    """Returns (payout, multiplier_for_ui)."""
    if outcome == "blackjack":
        mult = 2.5
        return stake * mult, mult
    if outcome == "win":
        mult = 2.0
        return stake * mult, mult
    if outcome == "push":
        return stake, 1.0
    return 0.0, 0.0


def split_rank_key(card: Card) -> str:
    """Pairing key for split (10 / face cards match)."""
    rank = card["rank"]
    if rank in ("10", "jack", "queen", "king"):
        return "ten"
    return rank


def can_split_cards(cards: list[Card]) -> bool:
    if len(cards) != 2:
        return False
    return split_rank_key(cards[0]) == split_rank_key(cards[1])


def can_double_cards(cards: list[Card], *, already_doubled: bool) -> bool:
    if already_doubled or len(cards) != 2:
        return False
    return True


def dealer_visible(dealer: list[Card], *, reveal: bool) -> list[Card]:
    if reveal:
        return [dict(c) for c in dealer]
    out: list[Card] = []
    for i, card in enumerate(dealer):
        c = dict(card)
        if i == 1:
            c["hidden"] = True
        out.append(c)
    return out
