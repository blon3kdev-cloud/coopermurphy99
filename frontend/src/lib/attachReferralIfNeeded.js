import { rewards } from './api'
import { clearStoredReferral, getStoredReferral } from './referral'

/** Link a new account to a referrer stored from ?ref= (best-effort). */
export async function attachReferralIfNeeded() {
  const ref = getStoredReferral()
  if (!ref) return
  try {
    await rewards.attachReferral(ref)
    clearStoredReferral()
  } catch {
    /* already referred, window closed, or invalid — keep silent */
  }
}
