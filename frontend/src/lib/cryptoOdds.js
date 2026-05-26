/**
 * Crypto odds — must stay aligned with `backend/app/crypto_odds.py` + fair-odds service.
 * Server is source of truth; client recalculates every tick using `fairOdds.effectiveVol`
 * and live `remainingSec` (time left is a major driver of quotes).
 */

export const CRYPTO_MARGIN = 0.7
export const CRYPTO_BTC_VOL = 1.6
/** Minimum multiplier to accept a crypto bet (must match backend). */
export const CRYPTO_MIN_ODDS = 1.1
const SECS_PER_YEAR = 365.25 * 24 * 3600

/** @type {Record<string, number>} */
export const CRYPTO_WINDOW_SEC = { '5m': 300, '30m': 1800, '24h': 86400 }

const TIME_URGENCY_EXP = 0.62
const MIN_TIME_FRAC = 0.02

function erf(x) {
  const sign = x >= 0 ? 1 : -1
  const ax = Math.abs(x)
  const t = 1 / (1 + 0.3275911 * ax)
  const y =
    1 -
    (((((1.061405429 * t - 1.453152027) * t + 1.421413741) * t - 0.284496736) * t +
      0.254829592) *
      t *
      Math.exp(-ax * ax))
  return sign * y
}

function normCdf(x) {
  return 0.5 * (1 + erf(x / Math.SQRT2))
}

export function cryptoWindowSeconds(windowKey) {
  if (!windowKey) return null
  return CRYPTO_WINDOW_SEC[windowKey] ?? null
}

export function timeUrgencyScale(remainingSec, windowSec) {
  if (!windowSec || windowSec <= 0) return 1
  const frac = Math.max(MIN_TIME_FRAC, Math.min(1, remainingSec / windowSec))
  return frac ** TIME_URGENCY_EXP
}

/**
 * @param {number} annualVol
 * @param {number} current
 * @param {number} openp
 * @param {number} remainingSec
 * @param {number | null | undefined} windowSec
 * @returns {{ up: number, down: number }}
 */
export function calcCryptoOddsWithVol(annualVol, current, openp, remainingSec, windowSec) {
  if (current <= 0 || openp <= 0 || remainingSec <= 0) {
    return { up: 1.40, down: 1.40 }
  }
  const vol = Math.max(0.01, Number(annualVol))
  const T = remainingSec / SECS_PER_YEAR
  const tScale = timeUrgencyScale(remainingSec, windowSec)
  const sigSqrtT = Math.max(1e-9, vol * Math.sqrt(T) * tScale)
  const d = Math.log(current / openp) / sigSqrtT
  const pUp = Math.max(0.01, Math.min(0.99, normCdf(d)))
  const pDown = 1 - pUp
  const quote = (p) =>
    Math.round(Math.min(15, Math.max(1.01, CRYPTO_MARGIN / p)) * 100) / 100
  return { up: quote(pUp), down: quote(pDown) }
}

/**
 * @param {string | null | undefined} windowKey
 * @param {Record<string, unknown> | null | undefined} serverOdds
 * @param {Record<string, unknown> | null | undefined} fairOdds
 * @param {number | null | undefined} current
 * @param {number | null | undefined} openp
 * @param {number} remainingSec
 */
export function pickCryptoOdds(windowKey, serverOdds, fairOdds, current, openp, remainingSec) {
  if (current == null || openp == null || remainingSec <= 0) {
    return { up: null, down: null, source: 'none' }
  }
  const windowSec =
    cryptoWindowSeconds(windowKey) ??
    (typeof fairOdds?.windowSec === 'number' ? fairOdds.windowSec : null)

  const eff = fairOdds?.effectiveVol
  if (typeof eff === 'number' && Number.isFinite(eff) && eff > 0) {
    const o = calcCryptoOddsWithVol(eff, current, openp, remainingSec, windowSec)
    return { ...o, source: 'dynamic' }
  }

  const up = serverOdds?.up
  const down = serverOdds?.down
  if (
    typeof up === 'number' &&
    typeof down === 'number' &&
    Number.isFinite(up) &&
    Number.isFinite(down)
  ) {
    return { up, down, source: 'server' }
  }

  const local = calcCryptoOdds(current, openp, remainingSec, windowKey)
  return { ...local, source: 'local' }
}

/** @param {string | null | undefined} windowKey */
export function calcCryptoOdds(current, openp, remainingSec, windowKey) {
  return calcCryptoOddsWithVol(
    CRYPTO_BTC_VOL,
    current,
    openp,
    remainingSec,
    cryptoWindowSeconds(windowKey),
  )
}

export function isCryptoOddsBettable(n) {
  return n != null && Number.isFinite(n) && n >= CRYPTO_MIN_ODDS
}

export function fmtCryptoOddsMult(n) {
  if (!isCryptoOddsBettable(n)) return '—'
  return (
    n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + 'x'
  )
}

/** Parse `crypto-k-btc-5m` → `5m`. */
export function cryptoWindowFromBetId(betId) {
  const id = String(betId).replace(/^crypto-/, '')
  const m = id.match(/^k-btc-(.+)$/)
  return m ? m[1] : null
}
