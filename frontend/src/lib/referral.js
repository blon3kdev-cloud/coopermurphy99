import { sanitizeReferralCode } from './safeUrl'

const STORAGE_KEY = 'cz_ref'

/** Persist ?ref= from the landing URL for post-registration attach. */
export function captureReferralFromUrl() {
  try {
    const ref = new URLSearchParams(window.location.search).get('ref')
    const code = sanitizeReferralCode(ref)
    if (code) sessionStorage.setItem(STORAGE_KEY, code)
  } catch {
    /* ignore */
  }
}

export function getStoredReferral() {
  try {
    return sessionStorage.getItem(STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

export function clearStoredReferral() {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    /* ignore */
  }
}
