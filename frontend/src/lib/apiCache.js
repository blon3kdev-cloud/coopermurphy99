/** In-memory GET cache with TTL — shared across route navigations. */

const store = new Map();

/**
 * @param {string} key
 * @returns {*|null}
 */
export function getCached(key) {
  const entry = store.get(key);
  if (!entry) return null;
  if (Date.now() > entry.expires) {
    store.delete(key);
    return null;
  }
  return entry.data;
}

/**
 * @param {string} key
 * @param {*} data
 * @param {number} ttlMs
 */
export function setCached(key, data, ttlMs) {
  store.set(key, { data, expires: Date.now() + ttlMs });
}

/**
 * @param {string} [prefix]
 */
export function invalidateCache(prefix) {
  if (!prefix) {
    store.clear();
    return;
  }
  for (const k of store.keys()) {
    if (k.startsWith(prefix)) store.delete(k);
  }
}

/**
 * @template T
 * @param {string} key
 * @param {() => Promise<T>} fetcher
 * @param {number} [ttlMs]
 * @returns {Promise<T>}
 */
export async function fetchWithCache(key, fetcher, ttlMs = 30_000) {
  const hit = getCached(key);
  if (hit != null) return hit;
  const data = await fetcher();
  setCached(key, data, ttlMs);
  return data;
}

/**
 * Return cached data immediately (if any), then refresh in background.
 * @template T
 * @param {string} key
 * @param {() => Promise<T>} fetcher
 * @param {(data: T) => void} onData
 * @param {number} [ttlMs]
 */
export function subscribeCached(key, fetcher, onData, ttlMs = 30_000) {
  const hit = getCached(key);
  if (hit != null) onData(hit);

  let alive = true;
  fetcher()
    .then((data) => {
      if (!alive) return;
      setCached(key, data, ttlMs);
      onData(data);
    })
    .catch(() => {});

  return () => {
    alive = false;
  };
}
