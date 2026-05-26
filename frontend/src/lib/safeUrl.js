import { API_BASE } from './api/config'

const REF_CODE_RE = /^[a-zA-Z0-9_-]{1,64}$/

/** Hosts allowed for remote images (API uploads, CDN, app origin). */
function allowedImageHosts() {
  const hosts = new Set(['czutkabet.com', 'www.czutkabet.com', 'localhost', '127.0.0.1'])
  if (typeof window !== 'undefined' && window.location?.host) {
    hosts.add(window.location.host)
  }
  if (API_BASE) {
    try {
      hosts.add(new URL(API_BASE).host)
    } catch {
      /* ignore */
    }
  }
  const extra = process.env.REACT_APP_IMAGE_HOSTS || ''
  extra.split(',').map((h) => h.trim()).filter(Boolean).forEach((h) => hosts.add(h))
  return hosts
}

function resolveUrl(raw) {
  const s = String(raw ?? '').trim()
  if (!s) return null
  try {
    if (s.startsWith('/')) {
      const base = API_BASE || (typeof window !== 'undefined' ? window.location.origin : '')
      return base ? new URL(s, base.endsWith('/') ? base : `${base}/`) : new URL(s, 'https://czutkabet.com/')
    }
    return new URL(s)
  } catch {
    return null
  }
}

const DATA_IMAGE_RE = /^data:image\/(png|jpe?g|webp|gif);base64,/i
/** ~2MB decoded — preset thumbnails from our scraper stay well under this. */
const MAX_DATA_IMAGE_LEN = 3_000_000

function safeDataImageUrl(raw) {
  const s = String(raw ?? '').trim()
  if (!s || !DATA_IMAGE_RE.test(s) || s.length > MAX_DATA_IMAGE_LEN) return null
  return s
}

/**
 * @param {string | null | undefined} raw
 * @returns {string | null} Safe https (or http in dev) image URL, inline data:image, or null.
 */
export function safeImageUrl(raw) {
  const inline = safeDataImageUrl(raw)
  if (inline) return inline

  const u = resolveUrl(raw)
  if (!u) return null

  const proto = u.protocol.toLowerCase()
  const allowHttp = process.env.NODE_ENV === 'development'
  if (proto === 'https:') {
    /* ok */
  } else if (allowHttp && proto === 'http:') {
    /* dev only */
  } else {
    return null
  }

  if (!allowedImageHosts().has(u.host)) return null
  return u.href
}

/**
 * Admin/local preview: https URLs via safeImageUrl, or data:image/* from FileReader.
 * @param {string | null | undefined} raw
 * @returns {string | null}
 */
export function safePreviewImageUrl(raw) {
  return safeDataImageUrl(raw) || safeImageUrl(raw)
}

const REFERRAL_HOST =
  (process.env.REACT_APP_REFERRAL_HOST || 'czutkabet.com').replace(/^https?:\/\//, '').split('/')[0]

/**
 * Build canonical referral link from a short code (not a full URL from API).
 * @param {string | null | undefined} code
 * @returns {string | null}
 */
function referralCodeFromApi(code) {
  const c = String(code ?? '').trim()
  if (REF_CODE_RE.test(c)) return c
  const m = c.match(/(?:\?|&)ref=([a-zA-Z0-9_-]{1,64})/i)
  return m ? sanitizeReferralCode(m[1]) : null
}

export function safeReferralUrl(code) {
  const c = referralCodeFromApi(code)
  if (!c) return null
  return `https://${REFERRAL_HOST}/?ref=${encodeURIComponent(c)}`
}

/**
 * @param {string | null | undefined} ref Query param value from ?ref=
 * @returns {string | null} Sanitized code safe to store, or null.
 */
export function sanitizeReferralCode(ref) {
  const c = String(ref ?? '').trim()
  return REF_CODE_RE.test(c) ? c : null
}

export { REF_CODE_RE }
