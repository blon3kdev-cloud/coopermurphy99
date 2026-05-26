/** Max length for search box input (client-side filter only). */
export const MAX_SEARCH_QUERY_LEN = 100;

/**
 * Normalize user search input: strip control chars, trim, cap length.
 * Used only for in-memory `.includes()` matching — never in SQL, shell, or HTML.
 */
export function sanitizeSearchQuery(raw) {
  return String(raw ?? '')
    .replace(/[\0-\x1f\x7f]/g, '')
    .trim()
    .slice(0, MAX_SEARCH_QUERY_LEN);
}

export function normalizeSearchQuery(raw) {
  return sanitizeSearchQuery(raw).toLowerCase();
}

/** True when every non-empty part of `query` appears in the joined haystack (substring match). */
export function textMatchesQuery(parts, query) {
  const q = normalizeSearchQuery(query);
  if (!q) return true;
  const hay = parts
    .filter(Boolean)
    .map((p) => String(p))
    .join(' ')
    .toLowerCase();
  return hay.includes(q);
}
