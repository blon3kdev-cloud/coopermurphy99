import { useEffect, useState } from 'react';
import { getCached, setCached } from '../lib/apiCache';

/**
 * Cached list fetch with explicit loading state (null until first resolve).
 * @template T
 * @param {string} cacheKey
 * @param {() => Promise<T>} fetcher
 * @param {number} [ttlMs]
 */
export function useCachedList(cacheKey, fetcher, ttlMs = 30_000) {
  const [data, setData] = useState(() => {
    const hit = getCached(cacheKey);
    return Array.isArray(hit) ? hit : null;
  });
  const [loading, setLoading] = useState(() => getCached(cacheKey) == null);

  useEffect(() => {
    let alive = true;
    const hit = getCached(cacheKey);
    if (Array.isArray(hit)) {
      setData(hit);
      setLoading(false);
    } else {
      setLoading(true);
    }

    fetcher()
      .then((raw) => {
        if (!alive) return;
        const list = Array.isArray(raw) ? raw : [];
        setCached(cacheKey, list, ttlMs);
        setData(list);
      })
      .catch(() => {
        if (!alive) return;
        setData([]);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps -- fetcher identity stable per page
  }, [cacheKey, ttlMs]);

  return { data, loading, setData };
}
