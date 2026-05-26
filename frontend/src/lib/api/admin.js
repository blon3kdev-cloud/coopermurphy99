import { adminApiCall } from './client'

export function login(creds) {
  return adminApiCall('/admin/login', {
    method: 'POST',
    body: JSON.stringify(creds ?? {}),
  })
}

export function logout() {
  return adminApiCall('/admin/logout', { method: 'POST', body: '{}' })
}

export function getStats(range) {
  return adminApiCall(`/admin/stats?range=${encodeURIComponent(range)}`)
}

export function getUsers() {
  return adminApiCall('/admin/users')
}

export function setUserStatus(username, status) {
  return adminApiCall(`/admin/users/${encodeURIComponent(username)}/status`, {
    method: 'POST',
    body: JSON.stringify({ status }),
  })
}

/** @param {string} username @param {number|null} oddsPercent or null to clear */
export function setUserCasinoOdds(username, oddsPercent) {
  return adminApiCall(`/admin/users/${encodeURIComponent(username)}/casino-odds`, {
    method: 'POST',
    body: JSON.stringify({ odds: oddsPercent }),
  })
}

export function getTransactions() {
  return adminApiCall('/admin/transactions')
}

export function refundWithdrawal(id) {
  return adminApiCall('/admin/withdrawals/refund', {
    method: 'POST',
    body: JSON.stringify({ id }),
  })
}

export function getAdminSettings() {
  return adminApiCall('/admin/settings')
}

export function patchAdminSettings(patch) {
  return adminApiCall('/admin/settings', {
    method: 'PATCH',
    body: JSON.stringify(patch ?? {}),
  })
}

export function getPendingBlikCodes() {
  return adminApiCall('/admin/blik/pending-codes')
}

export function redeemBlikCode(depositId, success, note) {
  return adminApiCall(`/admin/blik/deposits/${depositId}/redeem`, {
    method: 'POST',
    body: JSON.stringify({ success, note: note || undefined }),
  })
}

export function getBets() {
  return adminApiCall('/admin/bets')
}

export function getBetPlacements() {
  return adminApiCall('/admin/bet-placements')
}

export function createBet(form) {
  return adminApiCall('/admin/bets', {
    method: 'POST',
    body: JSON.stringify(form ?? {}),
  })
}

export function updateBet(id, patch) {
  return adminApiCall(`/admin/bets/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(patch ?? {}),
  })
}

export function getOddsSports() {
  return adminApiCall('/admin/odds/sports')
}

export function autoCreateBets({ sport, amount }) {
  return adminApiCall('/admin/bets/auto', {
    method: 'POST',
    body: JSON.stringify({ sport, amount }),
  })
}

export function createIsportsSession({ sport = 'football', amount = 5 } = {}) {
  return adminApiCall('/admin/isports/sessions', {
    method: 'POST',
    body: JSON.stringify({ sport, amount }),
  })
}

export function getIsportsSessionPage(sessionId, { page = 0, perPage = 1 } = {}) {
  const q = new URLSearchParams({ page: String(page), perPage: String(perPage) })
  return adminApiCall(`/admin/isports/sessions/${encodeURIComponent(sessionId)}?${q}`)
}

export function createIsportsMarkets(sessionId, { matchId, variants }) {
  return adminApiCall(`/admin/isports/sessions/${encodeURIComponent(sessionId)}/create`, {
    method: 'POST',
    body: JSON.stringify({ matchId, variants }),
  })
}

export function previewIsportsAutoResolve() {
  return adminApiCall('/admin/isports/auto-resolve/preview')
}

export function runIsportsAutoResolve() {
  return adminApiCall('/admin/isports/auto-resolve', { method: 'POST', body: '{}' })
}

export function resolveBet(id, outcome) {
  return adminApiCall(`/admin/bets/${encodeURIComponent(id)}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ outcome }),
  })
}

export function deleteBet(id) {
  return adminApiCall(`/admin/bets/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function getKrypto() {
  return adminApiCall('/admin/games/crypto')
}

export function getKasyno() {
  return adminApiCall('/admin/games/casino')
}

export function getPresets({ q, codes } = {}) {
  const params = new URLSearchParams()
  if (q?.trim()) params.set('q', q.trim())
  if (codes && codes !== 'all') params.set('codes', codes)
  const qs = params.toString()
  return adminApiCall(`/admin/presets${qs ? `?${qs}` : ''}`)
}

export function createPreset(preset) {
  return adminApiCall('/admin/presets', {
    method: 'POST',
    body: JSON.stringify(preset ?? {}),
  })
}

export function updatePreset(id, preset) {
  return adminApiCall(`/admin/presets/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(preset ?? {}),
  })
}

export function deletePreset(id) {
  return adminApiCall(`/admin/presets/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function getCodes() {
  return adminApiCall('/admin/codes')
}

export function createCode({ amountPln, maxUses, label }) {
  return adminApiCall('/admin/codes', {
    method: 'POST',
    body: JSON.stringify({
      amountPln,
      maxUses,
      label: label || undefined,
    }),
  })
}

export function getDailyCodeSettings() {
  return adminApiCall('/admin/codes/daily-settings')
}

export function patchDailyCodeSettings({ amountPln, maxUses }) {
  return adminApiCall('/admin/codes/daily-settings', {
    method: 'PATCH',
    body: JSON.stringify({ amountPln, maxUses }),
  })
}
