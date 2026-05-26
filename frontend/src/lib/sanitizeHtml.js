import DOMPurify from 'dompurify';

const PURIFY_OPTS = { ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'span', 'br'], ALLOWED_ATTR: ['class'] };

export function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Any API-driven or user string used with innerHTML must go through sanitizeHtml or escapeHtml. */
export function sanitizeHtml(str) {
  return DOMPurify.sanitize(String(str ?? ''), PURIFY_OPTS);
}

/** Trusted app-generated currency icon markup (img only). */
export function sanitizeTrustedSvg(str) {
  return DOMPurify.sanitize(String(str ?? ''), {
    ALLOWED_TAGS: ['img'],
    ALLOWED_ATTR: ['src', 'alt', 'class', 'width', 'height', 'decoding'],
  });
}
