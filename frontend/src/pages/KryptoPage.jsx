import React, { useDeferredValue, useMemo, useState } from 'react';
import CategoryPageHeader from '../components/category-page-header/CategoryPageHeader';
import MarketSearch from '../components/market-search/MarketSearch';
import EmptyState from '../components/empty-state/EmptyState';
import PageContentLoader from '../components/page-loader/PageContentLoader';
import '../components/featured-krypto/FeaturedKrypto.css';
import { KryptoBetCard } from '../lib/KryptoBetCard';
import { crypto as cryptoApi } from '../lib/api';
import { filterCryptoItems } from '../lib/marketFilters';
import { useCachedList } from '../hooks/useCachedList';
import './KryptoPage.css';

function KryptoPage() {
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);
  const isFiltering = deferredQuery !== query;

  const { data: items, loading } = useCachedList(
    'crypto:all',
    () => cryptoApi.list(),
    15_000,
  );

  const visible = useMemo(
    () => filterCryptoItems(items ?? [], deferredQuery),
    [items, deferredQuery],
  );
  const listLoading = loading || isFiltering;
  const hasSearch = Boolean(String(deferredQuery || '').trim());
  const tiles = visible.map((b, i) => ({ ...b, rowKey: `${b.id}-${i}` }));

  return (
    <>
      <CategoryPageHeader title="Crypto" className="category-page-header--spacious-back" />
      <MarketSearch query={query} onQueryChange={setQuery} />

      <PageContentLoader loading={listLoading}>
        <section className="featured-krypto krypto-explorer-page" aria-labelledby="krypto-page-heading">
          <div className="featured-krypto__inner">
            <h2 id="krypto-page-heading" className="featured-krypto__heading krypto-explorer-page__title">
              All markets
            </h2>
            {!listLoading && items && items.length === 0 ? (
              <EmptyState
                title="No crypto markets"
                hint="There are no open rounds right now — check back soon."
              />
            ) : !listLoading && items && visible.length === 0 ? (
              <EmptyState
                title="No matching crypto markets"
                hint={hasSearch ? 'Try another keyword or clear your search.' : undefined}
              />
            ) : (
              <div className="featured-krypto__grid">
                {tiles.map(({ rowKey, ...bet }) => (
                  <KryptoBetCard key={rowKey} {...bet} />
                ))}
              </div>
            )}
          </div>
        </section>
      </PageContentLoader>
    </>
  );
}

export default KryptoPage;
