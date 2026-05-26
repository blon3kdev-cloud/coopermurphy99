/** URL segment → `CasinoGame` engine id */
export const kasynoSlugToEngine = {
  keno: 'keno',
  limbo: 'limbo',
  dice: 'dice',
  crash: 'crash',
  blackjack21: 'blackjack',
  blackjack: 'blackjack',
  blitz: 'blitz',
};

/** Playable originals — keep in sync with `CasinoGame` engines. */
export const KASYNO_AVAILABLE = [
  { slug: 'keno', title: 'Keno', featuredTitle: 'KENO' },
  { slug: 'limbo', title: 'Limbo', featuredTitle: 'LIMBO' },
  { slug: 'crash', title: 'Crash', featuredTitle: 'CRASH' },
  { slug: 'dice', title: 'Dice', featuredTitle: 'DICE' },
  { slug: 'blackjack21', title: '21', featuredTitle: '21' },
  { slug: 'blitz', title: 'Blitz', featuredTitle: 'BLITZ' },
];

export const KASYNO_COMING_SOON = [
  { slug: 'auta', title: 'Auta', featuredTitle: 'AUTA' },
  { slug: 'hilo', title: 'HiLo', featuredTitle: 'HILO' },
];

export function resolveKasynoEngine(slug) {
  if (!slug) return null;
  return kasynoSlugToEngine[slug] ?? null;
}
