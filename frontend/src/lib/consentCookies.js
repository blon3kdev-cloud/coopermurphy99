const DEFAULT_MAX_AGE_DAYS = 365;

/** @param {string} name @param {string} value @param {number} [days] */
export function setConsentCookie(name, value, days = DEFAULT_MAX_AGE_DAYS) {
  const maxAge = Math.floor(days * 24 * 60 * 60);
  document.cookie = `${name}=${encodeURIComponent(value)};path=/;max-age=${maxAge};SameSite=Lax`;
}

/** @param {string} name */
export function getConsentCookie(name) {
  try {
    const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
    return match ? decodeURIComponent(match[1]) : null;
  } catch {
    return null;
  }
}

export const COOKIE_CONSENT_KEY = 'cz_cookie_consent';
export const AGE_VERIFIED_KEY = 'cz_age_verified';

export function hasCookieConsent() {
  return getConsentCookie(COOKIE_CONSENT_KEY) === '1';
}

export function acceptCookieConsent() {
  setConsentCookie(COOKIE_CONSENT_KEY, '1');
}

export function hasAgeVerified() {
  return getConsentCookie(AGE_VERIFIED_KEY) === 'yes';
}

export function setAgeVerified() {
  setConsentCookie(AGE_VERIFIED_KEY, 'yes');
}

export function exitSiteAfterAgeDenial() {
  try {
    window.location.replace('about:blank');
  } catch {
    window.location.href = 'about:blank';
  }
}
