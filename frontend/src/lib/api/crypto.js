import { fetchWithCache, invalidateCache } from '../apiCache'
import { apiCall } from './client'

const FEATURED_TTL = 10_000
const LIST_TTL = 15_000

export function listFeatured() {
  return fetchWithCache(
    'crypto:featured',
    () => apiCall('/crypto-bets/featured'),
    FEATURED_TTL,
  )
}

export function list() {
  return fetchWithCache('crypto:all', () => apiCall('/crypto-bets'), LIST_TTL)
}

export function invalidateLists() {
  invalidateCache('crypto:')
}

/** @param {{ window: string; direction: 'up' | 'down'; stakePln: number }} payload */
export function place(payload) {
  return apiCall('/crypto-bets/place', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
