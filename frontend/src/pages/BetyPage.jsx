import React, {
  useCallback,
  useDeferredValue,
  useEffect,
  useMemo,
  useState,
} from 'react';
import CategoryPageHeader from '../components/category-page-header/CategoryPageHeader';
import MarketSearch from '../components/market-search/MarketSearch';
import EmptyState from '../components/empty-state/EmptyState';
import PageContentLoader from '../components/page-loader/PageContentLoader';
import '../components/featured-bets/FeaturedBets.css';
import { FeaturedBetCard } from '../components/featured-bets/FeaturedBets';
import { markets } from '../lib/api';
import { MARKETS_PAGE_SIZE } from '../lib/api/markets';
import { getCached } from '../lib/apiCache';
import { filterMarkets, filtersFromMarkets } from '../lib/marketFilters';
import { useInfiniteScroll } from '../hooks/useInfiniteScroll';
import './BetyPage.css';

function firstPageFromCache() {
  const hit = getCached(`markets:page:${MARKETS_PAGE_SIZE}`);
  if (!hit) return { items: null, nextCursor: null };
  if (Array.isArray(hit)) return { items: hit, nextCursor: null };
  return {
    items: Array.isArray(hit.items) ? hit.items : null,
    nextCursor: hit.nextCursor ?? null,
  };
}

function BetyPage() {
  const cached = firstPageFromCache();
  const [items, setItems] = useState(cached.items);
  const [nextCursor, setNextCursor] = useState(cached.nextCursor);
  const [loading, setLoading] = useState(cached.items == null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [activeFilterId, setActiveFilterId] = useState('');
  const [query, setQuery] = useState('');

  const loadPage = useCallback(async (cursor, { append = false } = {}) => {
    const isMore = Boolean(cursor);
    if (isMore) setLoadingMore(true);
    else if (!append) setLoading(true);

    try {
      const page = await markets.list({ cursor });
      setItems((prev) => (append && prev ? [...prev, ...page.items] : page.items));
      setNextCursor(page.nextCursor);
    } catch {
      if (!append) setItems([]);
      setNextCursor(null);
    } finally {
      if (isMore) setLoadingMore(false);
      else setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (cached.items != null) return;
    loadPage(null);
  }, [cached.items, loadPage]);

  const loadMore = useCallback(() => {
    if (!nextCursor || loadingMore || loading) return;
    loadPage(nextCursor, { append: true });
  }, [nextCursor, loadingMore, loading, loadPage]);

  const hasMore = Boolean(nextCursor);
  const sentinelRef = useInfiniteScroll({
    hasMore,
    loading: loadingMore || loading,
    onLoadMore: loadMore,
  });

  const deferredFilterId = useDeferredValue(activeFilterId);
  const deferredQuery = useDeferredValue(query);
  const isFiltering =
    deferredFilterId !== activeFilterId || deferredQuery !== query;

  const filterChips = useMemo(
    () => (items ? filtersFromMarkets(items) : []),
    [items],
  );

  useEffect(() => {
    setActiveFilterId((prev) => (
      prev === '' || filterChips.some((c) => c.id === prev) ? prev : ''
    ));
  }, [filterChips]);

  const visible = useMemo(() => {
    if (!items) return [];
    return filterMarkets(items, {
      categoryId: deferredFilterId,
      query: deferredQuery,
    });
  }, [items, deferredFilterId, deferredQuery]);

  const listLoading = loading || isFiltering;
  const cards = visible.map((c, i) => ({ ...c, rowKey: `${c.id}-${i}` }));

  return (
    <>
      <CategoryPageHeader title="Bets" />
      <MarketSearch
        filterChips={filterChips}
        activeFilterId={activeFilterId}
        onFilterChange={setActiveFilterId}
        query={query}
        onQueryChange={setQuery}
      />

      <PageContentLoader loading={listLoading}>
        <section className="featured-bets bety-explorer" aria-labelledby="bety-page-heading">
          <div className="featured-bets__inner">
            <div className="featured-bets__header bety-explorer__header">
              <h2 id="bety-page-heading" className="featured-bets__heading">
                Bets for today
              </h2>
            </div>
            {!listLoading && items && items.length === 0 ? (
              <EmptyState
                title="No bets to show"
                hint="There are no open markets right now — check back soon."
              />
            ) : !listLoading && items && visible.length === 0 ? (
              <EmptyState
                title="No bets in this category"
                hint="Pick another filter or clear your search."
              />
            ) : (
              <>
                <div className="featured-bets__grid">
                  {cards.map(({ rowKey, ...market }) => (
                    <FeaturedBetCard key={rowKey} market={market} />
                  ))}
                </div>
                {hasMore && (
                  <div
                    ref={sentinelRef}
                    className="feed-scroll-sentinel"
                    aria-hidden={!loadingMore}
                  >
                    {loadingMore && (
                      <p className="feed-scroll-sentinel__label">Loading more…</p>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        </section>
      </PageContentLoader>
    </>
  );
}

export default BetyPage;
