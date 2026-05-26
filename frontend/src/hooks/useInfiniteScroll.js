import { useEffect, useRef } from 'react';

/**
 * Observe a sentinel and call onLoadMore when it enters the viewport.
 * @param {{ hasMore: boolean; loading: boolean; onLoadMore: () => void; rootMargin?: string }} opts
 */
export function useInfiniteScroll({ hasMore, loading, onLoadMore, rootMargin = '240px' }) {
  const sentinelRef = useRef(null);
  const onLoadMoreRef = useRef(onLoadMore);
  onLoadMoreRef.current = onLoadMore;

  useEffect(() => {
    const el = sentinelRef.current;
    if (!el || !hasMore) return undefined;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting && !loading) {
          onLoadMoreRef.current();
        }
      },
      { rootMargin },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [hasMore, loading, rootMargin]);

  return sentinelRef;
}
