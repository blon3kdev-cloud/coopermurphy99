/** Read double-submit CSRF token from document.cookie (set by API on login). */
export function getCsrfToken() {
  try {
    const match = document.cookie.match(/(?:^|;\s*)cz_csrf=([^;]*)/)
    return match ? decodeURIComponent(match[1]) : ''
  } catch {
    return ''
  }
}
