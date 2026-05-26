import { getCsrfToken } from '../csrf'
import { onAdminUnauthorized } from '../adminAuth'
import { getAuthHeaders, onUnauthorized } from '../betsApi'
import { apiUrl } from './config'

export class ApiError extends Error {
  /** @param {number} status @param {*} body */
  constructor(status, body) {
    const raw =
      typeof body === 'string'
        ? body
        : body?.detail ?? body?.error ?? `Request failed (${status})`
    const friendly = {
      internal_error: 'A server error occurred. Refresh the page and try again.',
      'no activity in period': 'No bets in this period — place a bet to unlock the bonus.',
      'already redeemed': 'You have already redeemed this code.',
      'invalid or used code': 'Invalid or already used code.',
      'code expired': 'Code has expired.',
      csrf_required: 'Session expired. Refresh the page and try again.',
      redeem_locked: 'Too many invalid codes. Try again in about 30 minutes.',
      validation_failed: 'Invalid request format. Refresh the page and try again.',
      insufficient_balance: 'Insufficient balance to place this bet.',
      'insufficient balance': 'Insufficient balance to place this bet.',
      'invalid code': 'Invalid login code.',
      'dev user missing — restart backend': 'Dev user missing — restart the backend.',
    }
    const detail = friendly[raw] ?? raw
    super(typeof detail === 'string' ? detail : JSON.stringify(detail))
    this.status = status
    this.body = body
  }
}

function buildHeaders(init, isAdmin) {
  const headers = {
    ...getAuthHeaders(),
    ...(init?.headers || {}),
  }
  const csrf = getCsrfToken()
  if (csrf) headers['X-CSRF-Token'] = csrf
  if (init?.body instanceof FormData) {
    delete headers['Content-Type']
  }
  return headers
}

/**
 * @param {string} path
 * @param {RequestInit} [init]
 */
export async function apiCall(path, init) {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: buildHeaders(init, false),
    credentials: 'include',
  })
  const text = await res.text()
  /** @type {*} */
  let body = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }

  if (!res.ok) {
    if (res.status === 401) onUnauthorized()
    throw new ApiError(res.status, body)
  }
  return body
}

/**
 * @param {string} path
 * @param {RequestInit} [init]
 */
export async function adminApiCall(path, init) {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: buildHeaders(init, true),
    credentials: 'include',
  })
  const text = await res.text()
  /** @type {*} */
  let body = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }

  if (!res.ok) {
    if (res.status === 401) onAdminUnauthorized()
    throw new ApiError(res.status, body)
  }
  return body
}
