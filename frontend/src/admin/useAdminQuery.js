import { useCallback, useEffect, useState } from 'react';

/**
 * Fetch admin page data with a loading flag (navigate first, load after).
 * @param {() => Promise<*> | *} fetcher
 * @param {import('react').DependencyList} [deps]
 */
export function useAdminQuery(fetcher, deps = []) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);

  const reload = useCallback(() => {
    setLoading(true);
    return Promise.resolve(fetcher())
      .then((result) => {
        setData(result);
        return result;
      })
      .catch(() => {
        setData(null);
        return null;
      })
      .finally(() => setLoading(false));
  }, deps);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    Promise.resolve(fetcher())
      .then((result) => {
        if (alive) setData(result);
      })
      .catch(() => {
        if (alive) setData(null);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, deps);

  return { loading, data, setData, reload };
}
