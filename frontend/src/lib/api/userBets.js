import { fetchWithCache, invalidateCache } from '../apiCache'
import { apiCall } from './client'

const ACTIVE_TTL = 8_000
const HISTORY_TTL = 20_000

export function getActive() {
  return fetchWithCache('user:bets:active', () => apiCall('/user/bets/active'), ACTIVE_TTL)
}

const HISTORY_PAGE_SIZE = 15

/** @param {{ before?: string | null; limit?: number }} [opts] */
export function getHistory(opts = {}) {
  const limit = opts.limit ?? HISTORY_PAGE_SIZE
  const before = opts.before ?? null
  const qs = new URLSearchParams({ limit: String(limit) })
  if (before) qs.set('before', before)
  const path = `/user/bets/history?${qs}`
  if (!before) {
    return fetchWithCache('user:bets:history', () => apiCall(path), HISTORY_TTL).then(
      normalizeHistoryPage,
    )
  }
  return apiCall(path).then(normalizeHistoryPage)
}

/** @param {unknown} res */
function normalizeHistoryPage(res) {
  if (Array.isArray(res)) {
    return { items: res, nextBefore: null }
  }
  return {
    items: Array.isArray(res?.items) ? res.items : [],
    nextBefore: res?.nextBefore ?? null,
  }
}

export { HISTORY_PAGE_SIZE }

export function getPendingCelebration() {
  return apiCall('/user/bets/celebration')
}

/** @param {string} celebrationKey */
export function dismissCelebration(celebrationKey) {
  return apiCall('/user/bets/celebration/dismiss', {
    method: 'POST',
    body: JSON.stringify({ celebrationKey }),
  })
}

export function invalidateUserBetsCache() {
  invalidateCache('user:bets')
}

/** @param {{ items: { marketId: string; side: 'yes' | 'no'; stakePln: number }[] }} slip */
export function placeSlip(slip) {
  return apiCall('/user/bets', {
    method: 'POST',
    body: JSON.stringify(slip),
  })
}

/**
 * Single-stake parlay — markets + crypto legs in one tasiemka.
 * @param {{ stakePln: number; markets?: { marketId: string; side: 'yes' | 'no' }[]; crypto?: { window: string; direction: 'up' | 'down' }[] }} slip
 */
export function placeParlay(slip) {
  return apiCall('/user/bets/parlay', {
    method: 'POST',
    body: JSON.stringify(slip),
  }).then((res) => {
    invalidateUserBetsCache()
    return res
  })
}
