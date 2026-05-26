const cardModules = require.context('../assets/cards', false, /\.png$/);

const SUIT_BY_LABEL = {
  Clubs: 'clubs',
  Diamonds: 'diamonds',
  Hearts: 'hearts',
  Spades: 'spades',
};

const SUIT_LABEL = {
  clubs: 'Clubs',
  diamonds: 'Diamonds',
  hearts: 'Hearts',
  spades: 'Spades',
};

const RANK_LABEL = {
  ace: 'Ace',
  '2': '2',
  '3': '3',
  '4': '4',
  '5': '5',
  '6': '6',
  '7': '7',
  '8': '8',
  '9': '9',
  '10': '10',
  jack: 'Jack',
  queen: 'Queen',
  king: 'King',
};

function cardFilename(suit, rank) {
  return `Suit=${SUIT_LABEL[suit]}, Number=${RANK_LABEL[rank]}.png`;
}

/** @type {Map<string, string>} */
const cardUrlBySuitRank = new Map();
/** @type {Map<string, string>} */
const cardUrlByRank = new Map();

for (const key of cardModules.keys()) {
  const url = cardModules(key);
  const match = /Suit=([^,]+), Number=([^./]+)\.png$/.exec(key);
  if (!match) continue;
  const suit = SUIT_BY_LABEL[match[1]];
  const rank = Object.entries(RANK_LABEL).find(([, label]) => label === match[2])?.[0];
  if (!suit || !rank) continue;
  cardUrlBySuitRank.set(`${suit}/${rank}`, url);
  if (!cardUrlByRank.has(rank)) cardUrlByRank.set(rank, url);
}

const SUIT_FALLBACK_ORDER = ['spades', 'hearts', 'diamonds', 'clubs'];

/** @param {'clubs'|'diamonds'|'hearts'|'spades'} suit @param {keyof RANK_LABEL} rank */
export function getCardImageUrl(suit, rank) {
  const normalizedRank = String(rank);
  const exact = cardUrlBySuitRank.get(`${suit}/${normalizedRank}`);
  if (exact) return exact;

  for (const fallbackSuit of SUIT_FALLBACK_ORDER) {
    const url = cardUrlBySuitRank.get(`${fallbackSuit}/${normalizedRank}`);
    if (url) return url;
  }

  const byRank = cardUrlByRank.get(normalizedRank);
  if (byRank) return byRank;

  return getCardBackUrl('blue');
}

/** @param {'blue'|'red'} [variant] */
export function getCardBackUrl(variant = 'blue') {
  const name =
    variant === 'red'
      ? 'Suit=Other, Number=Back Red.png'
      : 'Suit=Other, Number=Back Blue.png';
  return cardModules(`./${name}`);
}

const RANK_VALUES = {
  ace: 11,
  '2': 2,
  '3': 3,
  '4': 4,
  '5': 5,
  '6': 6,
  '7': 7,
  '8': 8,
  '9': 9,
  '10': 10,
  jack: 10,
  queen: 10,
  king: 10,
};

function normalizeRank(rank) {
  const key = String(rank ?? '').trim().toLowerCase();
  return key in RANK_VALUES ? key : '';
}

/** Single best hand total (matches backend ``hand_value``). */
export function handValue(cards) {
  const [total] = getHandTotals(cards);
  return total ?? 0;
}

/** @param {{ rank: keyof RANK_LABEL, hidden?: boolean }[]} cards */
export function getHandTotals(cards) {
  const visible = cards.filter((c) => !c.hidden);
  let low = 0;
  let high = 0;
  let aces = 0;

  for (const card of visible) {
    const rank = normalizeRank(card.rank);
    const v = RANK_VALUES[rank] ?? 0;
    if (rank === 'ace') aces += 1;
    low += rank === 'ace' ? 1 : v;
    high += v;
  }

  while (high > 21 && aces > 0) {
    high -= 10;
    aces -= 1;
  }

  if (low === high || high > 21) return [low];
  if (low <= 21 && high <= 21 && low !== high) return [low, high];
  return [high > 21 ? low : high];
}

/** @param {number[]} totals */
export function formatHandScore(totals) {
  if (!totals.length) return '0';
  const nums = totals.map((t) => Number(t)).filter((n) => Number.isFinite(n));
  if (!nums.length) return '0';
  if (nums.length === 1) return String(nums[0]);
  return nums.join(', ');
}
