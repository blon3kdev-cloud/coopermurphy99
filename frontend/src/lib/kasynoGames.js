/** URL segment → `CasinoGame` engine id */
export const kasynoSlugToEngine = {
  keno: 'keno',
  limbo: 'limbo',
  dice: 'dice',
  crash: 'crash',
  blackjack21: 'blackjack',
  blackjack: 'blackjack',
  blitz: 'blitz',
  dice2: 'dice2',
};

/** Playable originals — keep in sync with `CasinoGame` engines. */
export const KASYNO_AVAILABLE = [
  { slug: 'keno', title: 'Keno', featuredTitle: 'KENO' },
  { slug: 'limbo', title: 'Limbo', featuredTitle: 'LIMBO' },
  { slug: 'crash', title: 'Crash', featuredTitle: 'CRASH' },
  { slug: 'dice', title: 'Dice', featuredTitle: 'DICE' },
  { slug: 'blackjack21', title: '21', featuredTitle: '21' },
  { slug: 'blitz', title: 'Blitz', featuredTitle: 'BLITZ' },
  { slug: 'dice2', title: 'Dice2', featuredTitle: 'DICE2' },
];

export const KASYNO_COMING_SOON = [
  { slug: 'auta', title: 'Auta', featuredTitle: 'AUTA' },
  { slug: 'hilo', title: 'HiLo', featuredTitle: 'HILO' },
];

const FEATURED_KASYNO_SLUGS = ['keno', 'limbo', 'dice', 'dice2', 'blackjack21'];
const FEATURED_KASYNO_RANDOM_POOL = ['crash', 'blitz'];
export const FEATURED_KASYNO_MAX = 6;

/** Home featured row: fixed five + one random from the pool, max six. */
export function buildFeaturedKasynoGames(games = KASYNO_AVAILABLE) {
  const bySlug = new Map(games.map((g) => [g.slug, g]));
  const picked = FEATURED_KASYNO_SLUGS.map((slug) => bySlug.get(slug)).filter(Boolean);
  const pool = FEATURED_KASYNO_RANDOM_POOL.map((slug) => bySlug.get(slug)).filter(Boolean);
  if (pool.length && picked.length < FEATURED_KASYNO_MAX) {
    picked.push(pool[Math.floor(Math.random() * pool.length)]);
  }
  return picked.slice(0, FEATURED_KASYNO_MAX);
}

export function resolveKasynoEngine(slug) {
  if (!slug) return null;
  return kasynoSlugToEngine[slug] ?? null;
}
