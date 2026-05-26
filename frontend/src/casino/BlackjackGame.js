import { haptic } from '../lib/haptics.js';
import {
  formatHandScore,
  getCardBackUrl,
  getCardImageUrl,
  getHandTotals,
} from '../lib/cards.js';
import {
  doubleBlackjack,
  fetchActiveBlackjack,
  hitBlackjack,
  resetBlackjack,
  splitBlackjack,
  standBlackjack,
  startBlackjack,
} from '../lib/api/casino.js';
import { isUserSessionActive } from '../lib/betsApi.js';
import { optimisticBalanceDelta, refreshBalance } from '../lib/walletCurrency.js';
import { ApiError } from '../lib/api/client.js';
import sndBet from '../assets/audio/games/21/bet.mp3';
import sndDeal from '../assets/audio/games/21/deal.mp3';
import sndFlip from '../assets/audio/games/21/flip.mp3';
import sndMucked from '../assets/audio/games/21/mucked.mp3';

function playSound(src, vol = 0.6) {
  try {
    const a = new Audio(src);
    a.volume = vol;
    a.play().catch(() => {});
  } catch (_) {}
}

const FLY_MS = 480;
const DEAL_FLIP_MS = 520;
const FLIP_MS = 580;
const MUCK_STAGGER_MS = 95;
const MUCK_FADE_MS = 420;

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function nextFrame() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  });
}

function faceImg(card) {
  const img = document.createElement('img');
  img.className = 'bj-card__face bj-card__face--front';
  img.alt = `${card.rank} of ${card.suit}`;
  img.decoding = 'async';
  img.draggable = false;
  img.src = getCardImageUrl(card.suit, card.rank);
  return img;
}

function createCardEl(card, index) {
  const wrap = document.createElement('div');
  wrap.className = 'bj-card';
  wrap.style.setProperty('--bj-card-i', String(index));
  wrap.dataset.suit = card.suit;
  wrap.dataset.rank = card.rank;

  const flip = document.createElement('div');
  flip.className = 'bj-card__flip';

  const back = document.createElement('img');
  back.className = 'bj-card__face bj-card__face--back';
  back.alt = 'Face down card';
  back.decoding = 'async';
  back.draggable = false;
  back.src = getCardBackUrl('blue');

  flip.append(back, faceImg(card));
  wrap.append(flip);
  return wrap;
}

function setFlyFromDeck(cardEl, deckEl) {
  if (!deckEl) return;
  const deckRect = deckEl.getBoundingClientRect();
  const cardRect = cardEl.getBoundingClientRect();
  const dx = deckRect.left + deckRect.width * 0.5 - (cardRect.left + cardRect.width * 0.5);
  const dy = deckRect.top + deckRect.height * 0.5 - (cardRect.top + cardRect.height * 0.5);
  cardEl.style.setProperty('--bj-fly-x', `${dx}px`);
  cardEl.style.setProperty('--bj-fly-y', `${dy}px`);
}

function collectCardsInDealOrder(playerRow, dealerRow) {
  const p = [...(playerRow?.children ?? [])];
  const d = [...(dealerRow?.children ?? [])];
  const ordered = [];
  const n = Math.max(p.length, d.length);
  for (let i = 0; i < n; i += 1) {
    if (p[i]) ordered.push(p[i]);
    if (d[i]) ordered.push(d[i]);
  }
  return ordered;
}

function updateScoreBadge(scoreEl, cards, { dealerHole = false, emptyAsZero = false } = {}) {
  if (!scoreEl) return;
  const visible = cards.filter((c) => !c.hidden);
  if (!visible.length) {
    scoreEl.hidden = !emptyAsZero;
    scoreEl.textContent = '0';
    return;
  }
  if (dealerHole && cards.some((c) => c.hidden)) {
    const up = cards.find((c) => !c.hidden);
    scoreEl.hidden = false;
    scoreEl.textContent = up ? String(getHandTotals([up])[0]) : '0';
    pulseScore(scoreEl);
    return;
  }
  const totals = getHandTotals(cards);
  scoreEl.hidden = false;
  scoreEl.textContent = formatHandScore(totals);
  pulseScore(scoreEl);
}

function pulseScore(scoreEl) {
  scoreEl.classList.remove('bj__score--pop');
  void scoreEl.offsetWidth;
  scoreEl.classList.add('bj__score--pop');
}

function readCardsFromRow(row) {
  if (!row) return [];
  return [...row.querySelectorAll('.bj-card:not(.bj-card--muck)')].map((el) => ({
    suit: el.dataset.suit,
    rank: el.dataset.rank,
    hidden:
      el.dataset.hidden === 'true' ||
      el.classList.contains('bj-card--hole'),
  }));
}

function clearHandRow(row) {
  if (!row) return;
  row.innerHTML = '';
}

function clearScoreOutcomes(...scoreEls) {
  scoreEls.filter(Boolean).forEach((el) => {
    el.classList.remove(...BJ_SCORE_OUTCOME_CLASSES);
  });
}

function setScoresZero(...scoreEls) {
  const els = scoreEls.filter(Boolean);
  clearScoreOutcomes(...els);
  els.forEach((el) => {
    el.hidden = false;
    el.textContent = '0';
  });
}

function playerHasTwentyOne(cards) {
  return getHandTotals(cards).some((total) => total === 21);
}

function playerHandBust(cards) {
  const totals = getHandTotals(cards);
  return totals.length > 0 && totals.every((total) => total > 21);
}

function allPlayerHandsBust(handsOrState) {
  const hands = handsOrState?.hands?.length
    ? handsOrState.hands
    : [handsOrState?.player ?? handsOrState];
  return hands.length > 0 && hands.every((h) => playerHandBust(h));
}

const BJ_OUTCOME_BORDER_CLASS = {
  win: 'bj-card--outcome-win',
  blackjack: 'bj-card--outcome-win',
  lose: 'bj-card--outcome-loss',
  push: 'bj-card--outcome-push',
};

const BJ_SCORE_OUTCOME_CLASS = {
  win: 'bj__score--win',
  blackjack: 'bj__score--win',
  lose: 'bj__score--loss',
  push: 'bj__score--push',
};

const BJ_SCORE_OUTCOME_CLASSES = Object.values(BJ_SCORE_OUTCOME_CLASS);

function outcomeToModal(outcome, bet, payout) {
  const paid = Number(payout) || 0;
  if (outcome === 'lose') {
    return { won: false, mult: 0, profit: bet };
  }
  if (outcome === 'push') {
    return { tie: true };
  }
  const mult = bet > 0 ? paid / bet : 0;
  return { won: true, mult, profit: Math.max(0, paid - bet) };
}

export function mountBlackjackGame({ gameHost, shell }) {
  const root = document.createElement('div');
  root.className = 'bj bj--empty';
  root.innerHTML = `
    <div class="bj__table">
      <div class="bj__deck" data-bj-deck aria-hidden="true">
        <img class="bj__deck-card bj__deck-card--3" src="" alt="" />
        <img class="bj__deck-card bj__deck-card--2" src="" alt="" />
        <img class="bj__deck-card bj__deck-card--1" src="" alt="" />
      </div>
      <div class="bj__hand bj__hand--dealer" data-bj-dealer>
        <span class="bj__score" data-bj-score hidden>0</span>
        <div class="bj__cards" data-bj-cards></div>
      </div>
      <div class="bj__hand bj__hand--player" data-bj-player>
        <div class="bj__player-area">
          <div class="bj__split-hand bj__split-hand--0 bj__split-hand--active" data-bj-split-hand="0">
            <div class="bj__cards" data-bj-cards></div>
            <span class="bj__score" data-bj-score hidden>0</span>
          </div>
          <div class="bj__split-hand bj__split-hand--1" data-bj-split-hand="1" hidden>
            <div class="bj__cards" data-bj-cards></div>
            <span class="bj__score" data-bj-score hidden>0</span>
          </div>
        </div>
      </div>
    </div>
  `;

  const backUrl = getCardBackUrl('blue');
  root.querySelectorAll('.bj__deck-card').forEach((img) => {
    img.src = backUrl;
    img.alt = '';
  });

  gameHost.appendChild(root);

  const deckEl = root.querySelector('[data-bj-deck]');
  const dealerEl = root.querySelector('[data-bj-dealer]');
  const playerEl = root.querySelector('[data-bj-player]');
  const dealerRow = dealerEl?.querySelector('[data-bj-cards]');
  const splitHandEls = [...playerEl.querySelectorAll('[data-bj-split-hand]')];
  const splitRows = splitHandEls.map((el) => el.querySelector('[data-bj-cards]'));
  const splitScores = splitHandEls.map((el) => el.querySelector('[data-bj-score]'));
  const playerRow = splitRows[0];
  const dealerScore = dealerEl?.querySelector('[data-bj-score]');
  const playerScore = splitScores[0];
  const shellEl = shell.el;

  const btnHit = shellEl.querySelector('[data-bj-hit]');
  const btnStand = shellEl.querySelector('[data-bj-stand]');
  const btnSplit = shellEl.querySelector('[data-bj-split]');
  const btnDouble = shellEl.querySelector('[data-bj-double]');
  const btnBet = shellEl.querySelector('[data-crypto-postaw]');
  const actionsWrap = shellEl.querySelector('[data-bj-actions]');

  let state = {
    phase: 'idle',
    dealer: [],
    player: [],
    hands: null,
    activeHand: 0,
    split: false,
    doubled: [false],
    canHit: true,
    canDouble: false,
    canSplit: false,
    unitStake: 0,
    totalStake: 0,
    handOutcomes: null,
    outcome: null,
    payout: 0,
  };
  let animating = false;
  let dealInProgress = false;
  let actionInFlight = false;
  let lastBet = 0;
  let restoreInFlight = null;
  function setDeckDealing(on) {
    deckEl?.classList.toggle('bj__deck--dealing', on);
  }

  function setActionEnabled(btn, on) {
    if (!btn) return;
    btn.disabled = !on;
    btn.classList.toggle('crypto-casino__bj-btn--disabled', !on);
  }

  function setEmptyView(empty) {
    root.classList.toggle('bj--empty', empty);
  }

  function setSplitLayout(split) {
    root.classList.toggle('bj--split', split);
    if (splitHandEls[1]) splitHandEls[1].hidden = !split;
  }

  function activePlayerRow() {
    if (state.split) return splitRows[state.activeHand] ?? splitRows[0];
    return splitRows[0];
  }

  function updateActiveHandHighlight() {
    if (!state.split || state.phase !== 'playing') {
      splitHandEls.forEach((el) => {
        el.classList.remove('bj__split-hand--inactive', 'bj__split-hand--active');
        el.classList.add('bj__split-hand--active');
      });
      return;
    }
    splitHandEls.forEach((el, i) => {
      el.classList.toggle('bj__split-hand--active', i === state.activeHand);
      el.classList.toggle('bj__split-hand--inactive', i !== state.activeHand);
    });
  }

  function playerCardCountInDom() {
    if (state.split) {
      return splitRows.reduce((n, row) => n + (row?.children.length ?? 0), 0);
    }
    return splitRows[0]?.children.length ?? 0;
  }

  function domHandCounts() {
    return {
      player: playerCardCountInDom(),
      dealer: dealerRow?.children.length ?? 0,
    };
  }

  function visibleCardCount(row) {
    if (!row) return 0;
    return row.querySelectorAll('.bj-card:not(.bj-card--muck)').length;
  }

  function isHandsOutOfSyncFromData(data) {
    if (data.split && data.hands) {
      for (let i = 0; i < data.hands.length; i += 1) {
        if (visibleCardCount(splitRows[i]) !== data.hands[i].length) {
          return true;
        }
      }
      return visibleCardCount(dealerRow) !== data.dealer.length;
    }
    return (
      visibleCardCount(splitRows[0]) !== data.player.length
      || visibleCardCount(dealerRow) !== data.dealer.length
    );
  }

  function isHandsOutOfSync(playerCards, dealerCards) {
    if (state.split && state.hands) {
      for (let i = 0; i < state.hands.length; i += 1) {
        if (visibleCardCount(splitRows[i]) !== state.hands[i].length) {
          return true;
        }
      }
      return visibleCardCount(dealerRow) !== dealerCards.length;
    }
    return (
      visibleCardCount(splitRows[0]) !== playerCards.length
      || visibleCardCount(dealerRow) !== dealerCards.length
    );
  }

  function hasStuckAnimation() {
    if (!animating) return false;
    return !root.querySelector('.bj-card--flying, .bj-card--from-deck');
  }

  async function waitForCardAnimations() {
    const deadline = Date.now() + 8000;
    while (Date.now() < deadline) {
      if (!root.querySelector('.bj-card--flying, .bj-card--from-deck')) return;
      await wait(32);
    }
  }

  async function waitForDealComplete() {
    const deadline = Date.now() + 20000;
    while (dealInProgress && Date.now() < deadline) {
      await wait(32);
    }
    await waitForCardAnimations();
  }

  function isDealAnimationActive() {
    return dealInProgress
      || animating
      || Boolean(deckEl?.classList.contains('bj__deck--dealing'));
  }

  function tableHasCards() {
    return playerCardCountInDom() > 0 || (dealerRow?.children.length ?? 0) > 0;
  }

  async function prepareAction() {
    if (actionInFlight) return false;
    await restoreInFlight;
    await waitForDealComplete();
    if (dealInProgress || actionInFlight) return false;
    if (state.phase !== 'playing') {
      await ensurePlayableState();
      if (state.phase !== 'playing') return false;
      await waitForDealComplete();
    }
    if (actionInFlight) return false;
    return true;
  }

  async function appendMissingHandCards(handIndex, handCards) {
    const row = state.split ? splitRows[handIndex] : splitRows[0];
    if (!row || !handCards?.length) return;
    let visible = visibleCardCount(row);
    while (visible < handCards.length) {
      const card = handCards[visible];
      if (!card) break;
      await appendCard(row, card, visible, {
        hand: state.split ? `player-${handIndex}` : 'player',
      });
      visible += 1;
    }
    refreshScoresFromDom();
  }

  function forEachPlayerCard(cb) {
    splitRows.forEach((row) => {
      row?.querySelectorAll('.bj-card:not(.bj-card--muck)').forEach(cb);
    });
  }

  function clearOutcomeBorders() {
    clearScoreOutcomes(...splitScores);
    forEachPlayerCard((el) => {
      el.classList.remove(
        'bj-card--outcome-win',
        'bj-card--outcome-loss',
        'bj-card--outcome-push',
      );
    });
  }

  function lockCardsFaceUp(row) {
    row?.querySelectorAll('.bj-card:not(.bj-card--muck)').forEach((el) => {
      el.classList.remove('bj-card--hole', 'bj-card--revealing');
      el.classList.add('bj-card--face-up', 'bj-card--landed');
      el.dataset.hidden = 'false';
    });
  }

  function applyScoreOutcomes(outcome, handOutcomes) {
    clearScoreOutcomes(...splitScores);
    if (handOutcomes?.length) {
      handOutcomes.forEach((handOutcome, i) => {
        const cls = BJ_SCORE_OUTCOME_CLASS[handOutcome];
        if (cls && splitScores[i]) splitScores[i].classList.add(cls);
      });
      return;
    }
    const cls = BJ_SCORE_OUTCOME_CLASS[outcome];
    if (cls && splitScores[0]) splitScores[0].classList.add(cls);
  }

  function applyOutcomeBorders(outcome, handOutcomes) {
    clearOutcomeBorders();
    lockCardsFaceUp(dealerRow);
    splitRows.forEach((row) => lockCardsFaceUp(row));

    // Always prefer per-hand outcomes — never paint every card with the net round result.
    if (handOutcomes?.length) {
      handOutcomes.forEach((handOutcome, i) => {
        const cls = BJ_OUTCOME_BORDER_CLASS[handOutcome];
        if (!cls) return;
        splitRows[i]?.querySelectorAll('.bj-card:not(.bj-card--muck)').forEach((el) => {
          el.classList.add(cls);
        });
      });
      applyScoreOutcomes(outcome, handOutcomes);
      return;
    }

    const cls = BJ_OUTCOME_BORDER_CLASS[outcome];
    if (cls) {
      forEachPlayerCard((el) => {
        el.classList.add(cls);
      });
    }
    applyScoreOutcomes(outcome, handOutcomes);
  }

  function applyClearedRound(data) {
    if (data?.balances) refreshBalance(data.balances);
    shell.dismissResultModal?.();
    shell.clearGameError?.();
    resetToIdle();
  }

  async function tryServerRecover() {
    let data;
    try {
      data = await resetBlackjack();
    } catch (_) {
      return false;
    }
    if (data.reset || !data.active) {
      applyClearedRound(data);
      return true;
    }
    if (data.active && data.phase === 'playing') {
      await restoreSession(data, { animated: true, forceResync: true });
      return true;
    }
    applyClearedRound(data);
    return true;
  }

  function resetToIdle() {
    animating = false;
    dealInProgress = false;
    actionInFlight = false;
    state = {
      phase: 'idle',
      player: [],
      dealer: [],
      hands: null,
      activeHand: 0,
      split: false,
      doubled: [false],
      canHit: true,
      canDouble: false,
      canSplit: false,
      unitStake: 0,
      totalStake: 0,
      handOutcomes: null,
      outcome: null,
      payout: 0,
    };
    setDeckDealing(false);
    clearOutcomeBorders();
    setSplitLayout(false);
    clearHandRow(dealerRow);
    splitRows.forEach((row) => clearHandRow(row));
    setScoresZero(dealerScore, ...splitScores);
    if (splitScores[1]) splitScores[1].hidden = true;
    setEmptyView(true);
    syncControls();
  }

  function isRoundActive() {
    return (
      state.phase === 'playing'
      || state.phase === 'finished'
      || animating
      || dealInProgress
      || actionInFlight
    );
  }

  function syncControls() {
    const playing = state.phase === 'playing';
    const roundActive = isRoundActive();
    setEmptyView(
      !playing
      && !dealInProgress
      && !tableHasCards()
      && !deckEl?.classList.contains('bj__deck--dealing'),
    );
    if (actionsWrap) actionsWrap.hidden = !playing;
    shell.setRoundActive?.(roundActive);
    if (btnBet) {
      btnBet.textContent = 'Bet';
      btnBet.disabled = roundActive;
      btnBet.classList.toggle('crypto-casino__btn--disabled', roundActive);
    }
    const atTwentyOne = playing && state.canHit && playerHasTwentyOne(state.player);
    const actionsOn = playing
      && !animating
      && !dealInProgress
      && !actionInFlight
      && state.canHit
      && !atTwentyOne;
    setActionEnabled(btnHit, actionsOn);
    setActionEnabled(btnStand, playing && !animating && !dealInProgress && !actionInFlight);
    setActionEnabled(btnSplit, playing && !animating && !dealInProgress && !actionInFlight && state.canSplit);
    setActionEnabled(btnDouble, playing && !animating && !dealInProgress && !actionInFlight && state.canDouble);
  }

  /** Prefer server hand data when it matches the table; fall back to DOM while animating. */
  function cardsForScore(stateCards, row) {
    const domCards = readCardsFromRow(row);
    if (stateCards?.length && domCards.length === stateCards.length) {
      return stateCards;
    }
    return domCards.length ? domCards : (stateCards ?? []);
  }

  function refreshScoresFromDom() {
    const dealerCards = cardsForScore(state.dealer, dealerRow);
    const hole =
      dealerCards.length >= 2 && dealerCards.some((c) => c.hidden);
    if (state.split && state.hands) {
      state.hands.forEach((hand, i) => {
        updateScoreBadge(splitScores[i], cardsForScore(hand, splitRows[i]), {
          emptyAsZero: true,
        });
      });
    } else {
      updateScoreBadge(
        splitScores[0],
        cardsForScore(state.player, splitRows[0]),
        { emptyAsZero: true },
      );
    }
    updateScoreBadge(dealerScore, dealerCards, {
      dealerHole: hole,
      emptyAsZero: true,
    });
    updateActiveHandHighlight();
  }

  function placeCardInstant(row, card, index, { hole = false, hand = '' } = {}) {
    const el = createCardEl(card, index);
    if (hole) {
      el.classList.add('bj-card--hole', 'bj-card--landed');
      el.dataset.hidden = 'true';
    } else {
      el.classList.add('bj-card--face-up', 'bj-card--landed');
    }
    if (hand) el.dataset.bjHand = hand;
    el.dataset.bjIndex = String(index);
    row.appendChild(el);
    return el;
  }

  async function renderHandsInstant(playerCards, dealerCards) {
    clearOutcomeBorders();
    clearHandRow(dealerRow);
    splitRows.forEach((row) => clearHandRow(row));
    setEmptyView(false);

    const hole = Boolean(dealerCards[1]?.hidden);
    if (state.split && state.hands) {
      setSplitLayout(true);
      state.hands.forEach((hand, h) => {
        hand.forEach((card, i) => {
          placeCardInstant(splitRows[h], card, i, { hand: `player-${h}` });
        });
      });
    } else {
      setSplitLayout(false);
      playerCards.forEach((card, i) => {
        placeCardInstant(splitRows[0], card, i, { hand: 'player' });
      });
    }

    dealerCards.forEach((card, i) => {
      placeCardInstant(dealerRow, card, i, {
        hole: i === 1 && hole,
        hand: 'dealer',
      });
    });
    refreshScoresFromDom();
  }

  async function syncSplitHandsFromState(hands) {
    setSplitLayout(true);
    if (splitHandEls[1]) splitHandEls[1].hidden = false;

    const row0 = splitRows[0];
    const row1 = splitRows[1];
    if (row0?.children.length === 2 && hands.length === 2) {
      const moving = row0.children[1];
      if (moving && row1) {
        row1.appendChild(moving);
        moving.style.setProperty('--bj-card-i', '0');
        moving.dataset.bjIndex = '0';
      }
    }

    for (let h = 0; h < hands.length; h += 1) {
      const row = splitRows[h];
      const target = hands[h];
      for (let i = row.children.length; i < target.length; i += 1) {
        await appendCard(row, target[i], i, { hand: `player-${h}` });
        refreshScoresFromDom();
      }
    }
    updateActiveHandHighlight();
  }

  async function restoreSession(data, { animated = false, forceResync = false } = {}) {
    if (data.stakePln != null) lastBet = Number(data.stakePln) || lastBet;
    applyApiState(data);
    state.phase =
      data.phase === 'playing' || data.phase === 'finished' ? data.phase : 'idle';

    setSplitLayout(state.split);
    const outOfSync = isHandsOutOfSync(state.player, state.dealer);
    const useAnimation = animated || forceResync || outOfSync;

    if (useAnimation && outOfSync && domHandCounts().player + domHandCounts().dealer > 0) {
      await muckHands();
    }

    if (useAnimation && !state.split) {
      await dealOpeningHands(state.dealer, state.player, { clearPrevious: false });
    } else {
      await renderHandsInstant(state.player, state.dealer);
    }

    animating = false;
    setDeckDealing(false);
    syncControls();
    if (state.phase === 'playing') {
      await autoStandIfTwentyOne();
    }
  }

  async function reconcileFromServer({ animated = false } = {}) {
    if (isDealAnimationActive()) return false;
    let data;
    try {
      data = await fetchActiveBlackjack();
    } catch (_) {
      return false;
    }

    if (data.reset) {
      applyClearedRound(data);
      return false;
    }

    if (!data.active || data.phase !== 'playing') {
      if (state.phase === 'playing' || domHandCounts().player + domHandCounts().dealer > 0) {
        applyClearedRound(data);
      }
      return false;
    }

    if (state.phase === 'playing' && !isHandsOutOfSyncFromData(data)) {
      applyApiState(data);
      if (isHandsOutOfSync(data.player, data.dealer)) {
        await renderHandsInstant(data.player, data.dealer);
      }
      animating = false;
      setDeckDealing(false);
      syncControls();
      return true;
    }

    animating = false;
    shell.setLoading?.(false);
    await restoreSession(data, {
      animated,
      forceResync: isHandsOutOfSyncFromData(data),
    });
    return true;
  }

  async function ensurePlayableState() {
    await restoreInFlight;
    if (hasStuckAnimation()) {
      animating = false;
      syncControls();
    }

    if (isDealAnimationActive()) return;

    if (state.phase === 'playing') {
      const activeCards = state.split && state.hands
        ? state.hands[state.activeHand]
        : state.player;
      if (playerHandBust(activeCards)) {
        await reconcileFromServer();
        return;
      }
      if (!state.canHit && playerHasTwentyOne(activeCards)) {
        await onStand();
        return;
      }
    }

    if (state.phase === 'playing' && !isHandsOutOfSync(state.player, state.dealer)) {
      return;
    }

    if (state.phase === 'playing' && isHandsOutOfSync(state.player, state.dealer)) {
      const ok = await reconcileFromServer({ animated: true });
      if (!ok && state.phase === 'playing') {
        await tryServerRecover();
      }
      return;
    }

    if (state.phase !== 'playing') {
      try {
        const data = await fetchActiveBlackjack();
        if (data.reset) {
          applyClearedRound(data);
          return;
        }
        if (!data.active || data.phase !== 'playing') return;
        if (state.phase === 'playing' && !isHandsOutOfSyncFromData(data)) return;
        await restoreSession(data, { animated: true, forceResync: true });
      } catch (_) {
        /* ignore */
      }
    }
  }

  async function appendCard(row, card, index, { hole = false, hand = '' } = {}) {
    const el = createCardEl(card, index);
    if (hole) {
      el.classList.add('bj-card--hole');
      el.dataset.hidden = 'true';
    }
    if (hand) el.dataset.bjHand = hand;
    el.dataset.bjIndex = String(index);

    row.appendChild(el);
    el.classList.add('bj-card--from-deck');
    setFlyFromDeck(el, deckEl);

    playSound(sndDeal, 0.58);

    await nextFrame();
    el.classList.add('bj-card--flying');
    el.classList.remove('bj-card--from-deck');

    await wait(FLY_MS);
    el.classList.remove('bj-card--flying');
    el.classList.add('bj-card--landed');

    if (!hole) {
      playSound(sndFlip, 0.48);
      el.classList.add('bj-card--face-up');
      await wait(DEAL_FLIP_MS);
    }

    return el;
  }

  async function revealHoleCard(el) {
    if (!el || el.dataset.hidden !== 'true') return;
    haptic('light');
    playSound(sndFlip, 0.62);
    el.classList.add('bj-card--revealing');
    await wait(FLIP_MS);
    el.classList.remove('bj-card--hole', 'bj-card--revealing');
    el.classList.add('bj-card--face-up', 'bj-card--landed');
    el.dataset.hidden = 'false';
    if (state.dealer[1]) state.dealer[1] = { ...state.dealer[1], hidden: false };
    refreshScoresFromDom();
  }

  async function muckHands() {
    const playerCards = state.split
      ? [...(splitRows[0]?.children ?? []), ...(splitRows[1]?.children ?? [])]
      : [...(splitRows[0]?.children ?? [])];
    const cards = [...playerCards, ...(dealerRow?.children ?? [])].reverse();
    if (!cards.length) return;

    clearOutcomeBorders();
    playSound(sndMucked, 0.52);

    cards.forEach((el, i) => {
      if (!el.style.getPropertyValue('--bj-fly-x')) {
        setFlyFromDeck(el, deckEl);
      }
      el.style.setProperty('--bj-muck-i', String(i));
    });

    await nextFrame();

    for (let i = 0; i < cards.length; i += 1) {
      const el = cards[i];
      el.classList.add('bj-card--muck');
      refreshScoresFromDom();
      await wait(MUCK_STAGGER_MS);
    }

    await wait(MUCK_FADE_MS + cards.length * MUCK_STAGGER_MS);
    setScoresZero(dealerScore, ...splitScores);
    if (splitScores[1]) splitScores[1].hidden = true;
    setSplitLayout(false);
    clearHandRow(dealerRow);
    splitRows.forEach((row) => clearHandRow(row));
  }

  async function dealOpeningHands(
    dealerCards,
    playerCards,
    { clearPrevious = false, muckSnapshot = null } = {},
  ) {
    animating = true;
    setEmptyView(false);
    setDeckDealing(true);
    syncControls();

    try {
      const hadCards =
        (dealerRow?.children.length ?? 0) > 0 || playerCardCountInDom() > 0;

      if (clearPrevious && hadCards) {
        await muckHands();
      } else if (!hadCards) {
        setScoresZero(dealerScore, ...splitScores);
        clearHandRow(dealerRow);
        splitRows.forEach((row) => clearHandRow(row));
      }

      const dealCount = Math.max(playerCards.length, dealerCards.length, 2);
      for (let i = 0; i < dealCount; i += 1) {
        if (playerCards[i] && (playerRow?.children.length ?? 0) <= i) {
          await appendCard(playerRow, playerCards[i], i, { hand: 'player' });
          refreshScoresFromDom();
        }
        if (dealerCards[i] && (dealerRow?.children.length ?? 0) <= i) {
          const hole = i === 1 && Boolean(dealerCards[1]?.hidden);
          await appendCard(dealerRow, dealerCards[i], i, { hole, hand: 'dealer' });
          refreshScoresFromDom();
        }
      }
    } finally {
      setDeckDealing(false);
      animating = false;
      syncControls();
    }
  }

  async function revealDealerHand(dealerCards) {
    const holeEl = dealerRow?.children[1];
    if (holeEl && dealerCards[1] && !dealerCards[1].hidden) {
      await revealHoleCard(holeEl);
    }
    state.dealer = dealerCards.map((c) => ({ ...c, hidden: false }));
    for (let i = 2; i < dealerCards.length; i += 1) {
      await appendCard(dealerRow, dealerCards[i], i, { hand: 'dealer' });
      refreshScoresFromDom();
    }
    refreshScoresFromDom();
  }

  function applyApiState(data) {
    const split = Boolean(data.split);
    const hands = data.hands
      ? data.hands.map((h) => h.map((c) => ({ ...c })))
      : null;
    const activeHand = data.activeHand ?? 0;
    state = {
      phase: data.phase,
      player: (split && hands ? hands[activeHand] : data.player).map((c) => ({ ...c })),
      hands,
      activeHand,
      split,
      doubled: data.doubled ?? [false],
      canHit: data.canHit !== false,
      canDouble: Boolean(data.canDouble),
      canSplit: Boolean(data.canSplit),
      dealer: data.dealer.map((c) => ({ ...c })),
      unitStake: data.unitStakePln ?? (state.unitStake || lastBet),
      totalStake: data.stakePln ?? (state.totalStake || lastBet),
      handOutcomes: data.handOutcomes ?? null,
      outcome: data.outcome,
      payout: data.payout,
    };
    if (data.stakePln != null) lastBet = Number(data.stakePln) || lastBet;
    if (data.unitStakePln != null) {
      state.unitStake = Number(data.unitStakePln) || lastBet;
    }
    if (data.balances) refreshBalance(data.balances);
    const showSplitLayout = split || (data.handOutcomes?.length ?? 0) > 1;
    setSplitLayout(showSplitLayout);
    updateActiveHandHighlight();
  }

  async function completeFinishedRound() {
    if (state.phase !== 'finished' && !state.outcome) return;
    animating = true;
    syncControls();
    try {
      if (!allPlayerHandsBust(state)) {
        await revealDealerHand(state.dealer);
      }
      await showRoundResult();
    } finally {
      state.phase = 'idle';
      animating = false;
      syncControls();
    }
  }

  async function showRoundResult() {
    if (!state.outcome) return;
    if ((state.handOutcomes?.length ?? 0) > 1 || (state.hands?.length ?? 0) > 1) {
      setSplitLayout(true);
    }
    applyOutcomeBorders(state.outcome, state.handOutcomes);
    const totalBet = state.totalStake || lastBet;
    const modal = outcomeToModal(state.outcome, totalBet, state.payout);
    if (modal.tie) {
      shell.showResultModal?.(false, 0, 0, { tie: true });
      return;
    }
    shell.showResultModal?.(modal.won, modal.mult, modal.profit);
  }

  async function autoStandIfTwentyOne() {
    if (state.phase !== 'playing' || !state.canHit || !playerHasTwentyOne(state.player)) {
      return;
    }
    await onStand({ internal: true });
  }

  async function playRound() {
    await restoreInFlight;
    if (animating) {
      if (!hasStuckAnimation()) return;
      animating = false;
    }

    if (state.phase === 'playing') {
      await ensurePlayableState();
      if (state.phase === 'playing') return;
    }

    const bet = shell.getBetAmount();
    if (bet < 0.01) {
      haptic('warning');
      return;
    }

    shell.dismissResultModal?.();
    haptic('medium');
    playSound(sndBet, 0.55);
    optimisticBalanceDelta(-bet);
    setEmptyView(false);
    dealInProgress = true;
    syncControls();

    const muckSnapshot = {
      player: [...state.player],
      dealer: [...state.dealer],
    };
    const hadCards =
      (dealerRow?.children.length ?? 0) > 0 || (playerRow?.children.length ?? 0) > 0;
    if (hadCards) {
      await muckHands(muckSnapshot);
    } else {
      clearOutcomeBorders();
      setScoresZero(dealerScore, ...splitScores);
      clearHandRow(dealerRow);
      splitRows.forEach((row) => clearHandRow(row));
    }
    setDeckDealing(true);

    let data;
    try {
      data = await startBlackjack({ betAmount: bet });
    } catch (err) {
      dealInProgress = false;
      setDeckDealing(false);
      optimisticBalanceDelta(bet);
      haptic('warning');
      shell.showGameError?.(
        err instanceof ApiError ? err.message : 'Could not place bet',
      );
      syncControls();
      return;
    }

    shell.clearGameError?.();

    if (data.resumed) {
      try {
        await restoreSession(data, {
          animated: true,
          forceResync: isHandsOutOfSyncFromData(data),
        });
      } finally {
        dealInProgress = false;
        setDeckDealing(false);
        syncControls();
      }
      return;
    }

    lastBet = bet;
    applyApiState(data);
    state.unitStake = data.unitStakePln ?? bet;
    state.totalStake = data.stakePln ?? bet;
    syncControls();
    try {
      await dealOpeningHands(state.dealer, state.player, {
        clearPrevious: false,
      });
    } finally {
      dealInProgress = false;
      syncControls();
    }

    if (state.phase === 'finished') {
      await completeFinishedRound();
      return;
    }
    await autoStandIfTwentyOne();
  }

  async function onHit() {
    if (actionInFlight) return;
    if (!(await prepareAction())) return;

    actionInFlight = true;
    haptic('light');
    animating = true;
    syncControls();
    setDeckDealing(true);

    let data;
    try {
      data = await hitBlackjack();
    } catch (err) {
      setDeckDealing(false);
      animating = false;
      actionInFlight = false;
      syncControls();
      haptic('warning');
      if (err instanceof ApiError && /no active blackjack/i.test(err.message)) {
        await reconcileFromServer();
        if (state.phase === 'playing') await tryServerRecover();
      } else if (
        err instanceof ApiError
        && /hand is already 21|cannot hit/i.test(err.message)
      ) {
        await onStand();
      } else {
        shell.showGameError?.(
          err instanceof ApiError ? err.message : 'Could not hit',
        );
        if (state.phase === 'playing') await tryServerRecover();
      }
      return;
    }

    shell.clearGameError?.();

    const hitHand = state.activeHand;
    applyApiState(data);

    try {
      const handCards = state.split && state.hands
        ? state.hands[hitHand]
        : state.player;
      await appendMissingHandCards(hitHand, handCards);
      setDeckDealing(false);

      if (state.phase === 'finished') {
        await completeFinishedRound();
      } else if (state.split && state.activeHand !== hitHand) {
        refreshScoresFromDom();
      }
    } finally {
      animating = false;
      actionInFlight = false;
      syncControls();
    }
  }

  async function onDouble() {
    if (actionInFlight) return;
    if (!(await prepareAction())) return;
    if (!state.canDouble) return;

    actionInFlight = true;
    const doubledHand = state.activeHand;
    const unit = state.unitStake || lastBet;
    optimisticBalanceDelta(-unit);
    haptic('medium');
    animating = true;
    syncControls();
    setDeckDealing(true);

    let data;
    try {
      data = await doubleBlackjack();
    } catch (err) {
      optimisticBalanceDelta(unit);
      setDeckDealing(false);
      animating = false;
      actionInFlight = false;
      syncControls();
      haptic('warning');
      if (err instanceof ApiError && /no active blackjack/i.test(err.message)) {
        await reconcileFromServer();
        if (state.phase === 'playing') await tryServerRecover();
      } else {
        shell.showGameError?.(
          err instanceof ApiError ? err.message : 'Could not double',
        );
        if (state.phase === 'playing') await tryServerRecover();
      }
      return;
    }

    shell.clearGameError?.();
    const rowBefore = splitRows[doubledHand];
    const prevCount = rowBefore?.children.length ?? 0;
    applyApiState(data);

    try {
      const row = splitRows[doubledHand];
      const handCards = state.split && state.hands
        ? state.hands[doubledHand]
        : state.player;
      const card = handCards[handCards.length - 1];
      if (card && handCards.length > prevCount && row) {
        await appendCard(row, card, handCards.length - 1, {
          hand: state.split ? `player-${doubledHand}` : 'player',
        });
        refreshScoresFromDom();
      }
      setDeckDealing(false);

      if (state.phase === 'finished') {
        await completeFinishedRound();
      } else if (state.split && state.activeHand !== doubledHand) {
        refreshScoresFromDom();
      }
    } finally {
      animating = false;
      actionInFlight = false;
      syncControls();
    }
  }

  async function onSplit() {
    if (actionInFlight) return;
    if (!(await prepareAction())) return;
    if (!state.canSplit) return;

    actionInFlight = true;
    const unit = state.unitStake || lastBet;
    optimisticBalanceDelta(-unit);
    haptic('medium');
    animating = true;
    syncControls();
    setDeckDealing(true);

    let data;
    try {
      data = await splitBlackjack();
    } catch (err) {
      optimisticBalanceDelta(unit);
      setDeckDealing(false);
      animating = false;
      actionInFlight = false;
      syncControls();
      haptic('warning');
      if (err instanceof ApiError && /no active blackjack/i.test(err.message)) {
        await reconcileFromServer();
        if (state.phase === 'playing') await tryServerRecover();
      } else {
        shell.showGameError?.(
          err instanceof ApiError ? err.message : 'Could not split',
        );
        if (state.phase === 'playing') await tryServerRecover();
      }
      return;
    }

    shell.clearGameError?.();
    applyApiState(data);

    try {
      if (data.hands) {
        await syncSplitHandsFromState(data.hands);
      }
      setDeckDealing(false);
      await autoStandIfTwentyOne();
    } finally {
      animating = false;
      actionInFlight = false;
      syncControls();
    }
  }

  async function onStand({ internal = false } = {}) {
    if (!internal) {
      if (actionInFlight) return;
      if (!(await prepareAction())) return;
      actionInFlight = true;
    }

    animating = true;
    syncControls();

    const holeEl = dealerRow?.children[1];
    const holeFlip =
      holeEl?.dataset.hidden === 'true'
        ? revealHoleCard(holeEl)
        : Promise.resolve();

    let data;
    try {
      [data] = await Promise.all([standBlackjack(), holeFlip]);
    } catch (err) {
      animating = false;
      if (!internal) actionInFlight = false;
      syncControls();
      haptic('warning');
      if (err instanceof ApiError && /no active blackjack/i.test(err.message)) {
        await reconcileFromServer();
        if (state.phase === 'playing') await tryServerRecover();
      } else {
        shell.showGameError?.(
          err instanceof ApiError ? err.message : 'Could not stand',
        );
        if (state.phase === 'playing') await tryServerRecover();
      }
      return;
    }

    shell.clearGameError?.();
    applyApiState(data);

    try {
      if (state.phase === 'finished') {
        await completeFinishedRound();
      } else if (state.split) {
        refreshScoresFromDom();
      }
    } finally {
      animating = false;
      if (!internal) actionInFlight = false;
      syncControls();
    }
  }

  btnHit?.addEventListener('click', () => { onHit(); });
  btnStand?.addEventListener('click', () => { onStand(); });
  btnSplit?.addEventListener('click', () => { onSplit(); });
  btnDouble?.addEventListener('click', () => { onDouble(); });

  syncControls();

  async function tryRestoreActiveRound(attempt = 0) {
    if (!isUserSessionActive()) {
      if (attempt < 25) {
        await wait(120);
        return tryRestoreActiveRound(attempt + 1);
      }
      return;
    }
    if (restoreInFlight) return restoreInFlight;
    restoreInFlight = (async () => {
      try {
        if (isDealAnimationActive()) return;
        const data = await fetchActiveBlackjack();
        if (data.reset) {
          applyClearedRound(data);
          return;
        }
        if (!data.active || data.phase !== 'playing') return;
        if (state.phase === 'playing' && !isHandsOutOfSyncFromData(data)) {
          if (!isHandsOutOfSync(data.player, data.dealer)) return;
          applyApiState(data);
          await renderHandsInstant(data.player, data.dealer);
          syncControls();
          return;
        }
        if (isDealAnimationActive()) return;
        shell.setLoading?.(true);
        await restoreSession(data, {
          animated: true,
          forceResync: true,
        });
        shell.clearGameError?.();
      } catch (_) {
        /* retry on next visibility / focus */
      } finally {
        shell.setLoading?.(false);
        syncControls();
        restoreInFlight = null;
      }
    })();
    return restoreInFlight;
  }

  function onPageVisible() {
    if (document.visibilityState !== 'visible') return;
    void ensurePlayableState();
  }

  tryRestoreActiveRound();
  document.addEventListener('visibilitychange', onPageVisible);
  window.addEventListener('focus', onPageVisible);
  window.addEventListener('pageshow', onPageVisible);

  return {
    playRound,
    destroy() {
      document.removeEventListener('visibilitychange', onPageVisible);
      window.removeEventListener('focus', onPageVisible);
      window.removeEventListener('pageshow', onPageVisible);
      root.remove();
    },
  };
}
