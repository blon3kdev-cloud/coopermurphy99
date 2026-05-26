import { fetchWithCache } from '../apiCache'
import { apiCall } from './client'

const TTL = 30_000

export function listFeatured() {
  return fetchWithCache('markets:featured', () => apiCall('/markets/featured'), TTL)
}

const PAGE_SIZE = 24

/** @param {{ limit?: number; cursor?: string | null }} [opts] */
export function list(opts = {}) {
  const limit = opts.limit ?? PAGE_SIZE
  const cursor = opts.cursor ?? null
  if (!cursor) {
    const key = `markets:page:${limit}`
    const qs = new URLSearchParams({ limit: String(limit) })
    return fetchWithCache(key, () => apiCall(`/markets?${qs}`), TTL).then(normalizeMarketsPage)
  }
  const qs = new URLSearchParams({ limit: String(limit) })
  if (cursor) qs.set('cursor', cursor)
  return apiCall(`/markets?${qs}`).then(normalizeMarketsPage)
}

/** @param {unknown} res */
function normalizeMarketsPage(res) {
  if (Array.isArray(res)) {
    return { items: res, nextCursor: null }
  }
  return {
    items: Array.isArray(res?.items) ? res.items : [],
    nextCursor: res?.nextCursor ?? null,
  }
}

export { PAGE_SIZE as MARKETS_PAGE_SIZE }

export function get(id) {
  return apiCall(`/markets/${encodeURIComponent(id)}`)
}
