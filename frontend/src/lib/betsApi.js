/** @type {((mode: 'login' | 'register') => void) | null} */
let loginOpener = null

/** @type {(() => void) | null} */
let unauthorizedHandler = null

let hasUserSession = false

export function setLoginOpener(fn) {
  loginOpener = fn
}

export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

export function setUserSessionActive(active) {
  hasUserSession = Boolean(active)
}

export function onUnauthorized() {
  hasUserSession = false
  unauthorizedHandler?.()
}

/** Sync hint for guest gating — updated by App after /auth/session. */
export function isUserSessionActive() {
  return hasUserSession
}

/** Opens auth modal when guest; returns true if modal was opened. */
export function openAuthIfGuest(mode = 'login') {
  if (hasUserSession) return false
  loginOpener?.(mode)
  return true
}

/** Opens login modal when guest; returns true if login was prompted. */
export function openLoginIfGuest() {
  return openAuthIfGuest('login')
}

export function getAuthHeaders() {
  return { 'Content-Type': 'application/json' }
}

export async function getUserBalance() {
  const { apiUrl } = await import('./api/config')
  const { getCsrfToken } = await import('./csrf')
  const headers = { ...getAuthHeaders() }
  const csrf = getCsrfToken()
  if (csrf) headers['X-CSRF-Token'] = csrf
  const res = await fetch(apiUrl('/wallet/balance'), {
    headers,
    credentials: 'include',
  })
  if (!res.ok) throw new Error('balance fetch failed')
  return res.json()
}
