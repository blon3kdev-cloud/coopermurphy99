import { haptic } from '../lib/haptics.js';
import { getCardBackUrl, getCardImageUrl } from '../lib/cards.js';
import { playBlitz } from '../lib/api/casino.js';
import { blitzMultiplier, blitzWinAmounts } from '../lib/blitzOdds.js';
import { refreshBalance } from '../lib/walletCurrency.js';
import { ApiError } from '../lib/api/client.js';
import sndBet from '../assets/audio/games/21/bet.mp3';
import sndFlip from '../assets/audio/games/21/flip.mp3';
import sndWin from '../assets/audio/games/winlimbo.mp3';
import sndLose from '../assets/audio/games/lose.mp3';

const SUITS = ['clubs', 'spades', 'hearts', 'diamonds'];
/** 9 ranks × 4 suits — drops 2–5 from each suit (~31% fewer than 52). */
const BLITZ_RANKS = ['6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace'];
const DECK_SIZE = 36;
const GRID_COLS = 9;
const UNIQUE_MIN = 5;
const UNIQUE_MAX = DECK_SIZE;
const FLIP_MS = 125;
const PICK_GAP_MS = 72;
const FLIP_PITCH_STEP = 0.055;
const FLIP_PITCH_MAX = 2.1;

function playSound(src, vol = 0.55, playbackRate = 1) {
  try {
    const a = new Audio(src);
    a.volume = vol;
    a.playbackRate = playbackRate;
    a.play().catch(() => {});
  } catch (_) {}
}

function createFlipPitchPlayer() {
  let step = 0;
  return {
    reset() {
      step = 0;
    },
    play(src, vol = 0.48) {
      const rate = Math.min(FLIP_PITCH_MAX, 1 + step * FLIP_PITCH_STEP);
      step += 1;
      playSound(src, vol, rate);
      return rate;
    },
  };
}

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function indexToCard(i) {
  const idx = ((i % DECK_SIZE) + DECK_SIZE) % DECK_SIZE;
  return { suit: SUITS[Math.floor(idx / GRID_COLS)], rank: BLITZ_RANKS[idx % GRID_COLS] };
}

function fmtMult(n) {
  return `${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}x`;
}

function createGridCardEl(card, index) {
  const wrap = document.createElement('button');
  wrap.type = 'button';
  wrap.className = 'blitz-card bj-card';
  wrap.dataset.index = String(index);
  wrap.dataset.suit = card.suit;
  wrap.dataset.rank = card.rank;
  wrap.setAttribute('aria-label', `${card.rank} of ${card.suit}, face down`);
  wrap.disabled = true;

  const flip = document.createElement('div');
  flip.className = 'bj-card__flip';

  const back = document.createElement('img');
  back.className = 'bj-card__face bj-card__face--back';
  back.alt = '';
  back.decoding = 'async';
  back.draggable = false;
  back.src = getCardBackUrl('blue');

  const front = document.createElement('img');
  front.className = 'bj-card__face bj-card__face--front';
  front.alt = `${card.rank} of ${card.suit}`;
  front.decoding = 'async';
  front.draggable = false;
  front.src = getCardImageUrl(card.suit, card.rank);

  flip.append(back, front);
  wrap.append(flip);
  return wrap;
}

async function flipToFace(cardEl, flipPitch) {
  if (!cardEl || cardEl.classList.contains('bj-card--face-up')) return;
  haptic('light');
  flipPitch.play(sndFlip, 0.48);
  cardEl.classList.add('bj-card--revealing');
  await wait(FLIP_MS);
  cardEl.classList.remove('bj-card--revealing');
  cardEl.classList.add('bj-card--face-up', 'bj-card--landed');
  cardEl.setAttribute('aria-label', cardEl.querySelector('.bj-card__face--front')?.alt ?? 'Card');
}

async function flipToLossRed(cardEl, flipPitch) {
  if (!cardEl) return;
  haptic('medium');
  flipPitch.play(sndFlip, 0.58);
  const back = cardEl.querySelector('.bj-card__face--back');
  if (back) back.src = getCardBackUrl('red');
  cardEl.classList.remove('bj-card--face-up', 'bj-card--revealing');
  cardEl.classList.add('bj-card--revealing-loss');
  await wait(FLIP_MS);
  cardEl.classList.remove('bj-card--revealing-loss');
  cardEl.classList.add('bj-card--bust-red', 'bj-card--landed');
  cardEl.setAttribute('aria-label', 'Bust card');
}

function resetGridCards(cardEls) {
  const blue = getCardBackUrl('blue');
  cardEls.forEach((el) => {
    el.classList.remove(
      'bj-card--face-up',
      'bj-card--revealing',
      'bj-card--revealing-loss',
      'bj-card--bust-red',
      'bj-card--landed',
    );
    const back = el.querySelector('.bj-card__face--back');
    if (back) back.src = blue;
    const card = indexToCard(Number(el.dataset.index));
    el.setAttribute('aria-label', `${card.rank} of ${card.suit}, face down`);
  });
}

export function mountBlitzGame({ gameHost, shell }) {
  const root = document.createElement('div');
  root.className = 'blitz';
  root.innerHTML = `
    <div class="blitz__board">
      <div class="blitz__deck">
        <div class="blitz__grid" data-blitz-grid role="grid" aria-label="36 card deck"></div>
        <div class="blitz__progress" aria-hidden="true">
          <div class="blitz__progress-fill" data-blitz-progress></div>
        </div>
      </div>
    </div>
  `;

  const gridEl = root.querySelector('[data-blitz-grid]');
  const progressEl = root.querySelector('[data-blitz-progress]');
  const shellEl = shell.el;

  const cardEls = [];
  for (let i = 0; i < DECK_SIZE; i += 1) {
    const card = indexToCard(i);
    const el = createGridCardEl(card, i);
    cardEls.push(el);
    gridEl.appendChild(el);
  }

  gameHost.appendChild(root);

  let uniqueTarget = 5;
  let playing = false;
  let resultModalTimer = 0;
  let uniqueMultEl = null;
  let uniqueInputEl = null;
  const flipPitch = createFlipPitchPlayer();

  function hideResultModal() {
    if (resultModalTimer) {
      window.clearTimeout(resultModalTimer);
      resultModalTimer = 0;
    }
    shell.dismissResultModal?.();
  }

  function resetBoardForNewRound() {
    setProgress(0, false, true);
    resetGridCards(cardEls);
    flipPitch.reset();
    root.classList.remove('blitz--playing');
  }

  function syncSidebar() {
    const mult = blitzMultiplier(uniqueTarget);
    if (uniqueMultEl) uniqueMultEl.textContent = fmtMult(mult);
    if (uniqueInputEl) uniqueInputEl.value = String(uniqueTarget);
    const bet = shell.getBetAmount();
    shell.updateProfit?.(bet * (mult - 1));
  }

  function setProgress(ratio, lost = false, instant = false) {
    const pct = Math.max(0, Math.min(100, ratio * 100));
    if (instant) {
      progressEl.style.transition = 'none';
    }
    progressEl.style.width = `${pct}%`;
    progressEl.classList.toggle('blitz__progress-fill--loss', lost);
    if (instant) {
      void progressEl.offsetWidth;
      progressEl.style.transition = '';
    }
  }

  function bindSidebarControls() {
    uniqueMultEl = shellEl.querySelector('[data-blitz-mult]');
    uniqueInputEl = shellEl.querySelector('[data-blitz-unique]');
    const btnMinus = shellEl.querySelector('[data-blitz-unique-minus]');
    const btnPlus = shellEl.querySelector('[data-blitz-unique-plus]');

    const bump = (delta) => {
      if (playing) return;
      uniqueTarget = Math.min(UNIQUE_MAX, Math.max(UNIQUE_MIN, uniqueTarget + delta));
      syncSidebar();
      haptic('light');
    };

    btnMinus?.addEventListener('click', () => bump(-1));
    btnPlus?.addEventListener('click', () => bump(1));
    uniqueInputEl?.addEventListener('change', () => {
      if (playing) return;
      const n = Number.parseInt(uniqueInputEl.value, 10);
      if (Number.isFinite(n)) {
        uniqueTarget = Math.min(UNIQUE_MAX, Math.max(UNIQUE_MIN, n));
      }
      syncSidebar();
    });

    syncSidebar();
    shell.onBetChange?.(() => {
      if (!playing) syncSidebar();
    });
  }

  bindSidebarControls();

  async function animateRound(picks, won, target) {
    playing = true;
    root.classList.add('blitz--playing');
    flipPitch.reset();
    resetGridCards(cardEls);

    const revealed = new Set();
    let step = 0;

    for (let i = 0; i < picks.length; i += 1) {
      const pick = picks[i];
      const el = cardEls[pick];
      if (!el) continue;

      const isDuplicate = revealed.has(pick);
      if (!isDuplicate) {
        await flipToFace(el, flipPitch);
        revealed.add(pick);
        step += 1;
        setProgress(step / target, false);
        if (step >= target) break;
        await wait(PICK_GAP_MS);
        continue;
      }

      if (el.classList.contains('bj-card--face-up')) {
        await flipToLossRed(el, flipPitch);
      } else {
        await flipToFace(el, flipPitch);
        await wait(PICK_GAP_MS);
        await flipToLossRed(el, flipPitch);
      }
      setProgress(step / target, true);
      break;
    }

    playing = false;
    root.classList.remove('blitz--playing');
  }

  async function playRound() {
    hideResultModal();
    if (playing) return;
    resetBoardForNewRound();
    const bet = shell.getBetAmount();
    if (bet < 0.01) {
      shell.showGameError('Minimum bet is 0.01');
      return;
    }

    shell.clearGameError();

    shell.setLoading(true);
    playSound(sndBet, 0.5);

    let roundResult = null;
    try {
      const res = await playBlitz({ betAmount: bet, uniqueCards: uniqueTarget });
      const quotedMult = Number(res.multiplier) || blitzMultiplier(uniqueTarget);
      await animateRound(res.picks ?? [], Boolean(res.won), uniqueTarget);
      refreshBalance(res.balances?.PLN);
      const payout = Number(res.payout) || 0;
      const amounts = res.won
        ? blitzWinAmounts(bet, payout, quotedMult)
        : { mult: quotedMult, profit: 0 };
      if (res.won && uniqueMultEl) uniqueMultEl.textContent = fmtMult(amounts.mult);
      roundResult = {
        won: Boolean(res.won),
        mult: amounts.mult,
        profit: amounts.profit,
        bet,
      };
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Could not place bet';
      shell.showGameError(msg);
    } finally {
      shell.setLoading(false);
    }

    if (roundResult) {
      const { won, mult, profit, bet } = roundResult;
      playSound(won ? sndWin : sndLose, 0.72);
      haptic(won ? 'success' : 'medium');
      if (won) {
        shell.showResultModal(true, mult, profit);
      } else {
        shell.showResultModal(false, 0, bet);
      }
    }
  }

  return {
    playRound,
    destroy() {
      hideResultModal();
    },
  };
}
