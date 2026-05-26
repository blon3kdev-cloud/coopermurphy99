import { admin } from './api'

/** @type {(() => void) | null} */
let unauthorizedHandler = null

export function setAdminUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

export function onAdminUnauthorized() {
  unauthorizedHandler?.()
}

export async function adminLogout() {
  try {
    await admin.logout()
  } catch {
    /* ignore */
  }
}
