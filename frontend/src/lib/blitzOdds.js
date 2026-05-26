/** Blitz odds — keep in sync with backend `casino_rtp.blitz_multiplier`. */
export const BLITZ_DECK_SIZE = 36;
export const BLITZ_UNIQUE_MIN = 5;
export const BLITZ_TARGET_RTP = 0.8;
export const BLITZ_PAYOUT_EDGE = 0.99;

export function blitzWinChance(unique) {
  const n = Math.min(BLITZ_DECK_SIZE, Math.max(BLITZ_UNIQUE_MIN, unique));
  let p = 1;
  for (let j = 0; j < n; j += 1) {
    p *= (BLITZ_DECK_SIZE - j) / BLITZ_DECK_SIZE;
  }
  return p;
}

/** Total-return multiplier at default site RTP (e.g. 1.32× at 5 unique). */
export function blitzMultiplier(unique, rtp = BLITZ_TARGET_RTP) {
  const p = blitzWinChance(unique);
  if (p <= 0) return 1;
  const scaled = (rtp / p) * (BLITZ_PAYOUT_EDGE / BLITZ_TARGET_RTP);
  return Math.round(scaled * 100) / 100;
}

/** Win modal amounts from server payout (mult always matches profit). */
export function blitzWinAmounts(stake, payout, quotedMult) {
  const bet = Number(stake) || 0;
  const gross = Number(payout) || 0;
  if (bet > 0 && gross > 0) {
    const mult = Math.round((gross / bet) * 100) / 100;
    return { mult, profit: Math.max(0, Math.round((gross - bet) * 100) / 100) };
  }
  const mult = Number(quotedMult) || 1;
  return { mult, profit: 0 };
}
