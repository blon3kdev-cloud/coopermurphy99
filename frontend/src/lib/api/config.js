/** API base URL — empty uses same-origin `/api` (CRA dev proxy → backend). */
export const API_BASE = (process.env.REACT_APP_API_URL || '').replace(/\/$/, '')

export function apiUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}/api${p}`
}

export function wsUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`
  const base = API_BASE || (typeof window !== 'undefined' ? window.location.origin : '')
  const wsBase = base.replace(/^http/i, (m) => (m.toLowerCase() === 'https' ? 'wss' : 'ws'))
  return `${wsBase}/api${p}`
}
