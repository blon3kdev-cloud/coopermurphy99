import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { KryptoBetCard } from '../../lib/KryptoBetCard';
import EmptyState from '../empty-state/EmptyState';
import { crypto as cryptoApi } from '../../lib/api';
import { filterCryptoItems } from '../../lib/marketFilters';
import { getCached, subscribeCached } from '../../lib/apiCache';
import './FeaturedKrypto.css';

function FeaturedKrypto({ query = '' }) {
  const cached = getCached('crypto:featured');
  const [items, setItems] = useState(() => (Array.isArray(cached) ? cached : null));
  const visible = useMemo(
    () => filterCryptoItems(items ?? [], query),
    [items, query],
  );
  const hasSearch = Boolean(String(query || '').trim());

  useEffect(() => {
    return subscribeCached(
      'crypto:featured',
      () => cryptoApi.listFeatured(),
      (data) => setItems(Array.isArray(data) ? data : []),
      10_000,
    );
  }, []);

  return (
    <section className="featured-krypto" aria-labelledby="featured-krypto-heading">
      <div className="featured-krypto__inner">
        <div className="featured-krypto__header">
          <h2 id="featured-krypto-heading" className="featured-krypto__heading">
            Most popular in Crypto
          </h2>
          <Link
            className="featured-krypto__view-all"
            to="/crypto"
            aria-label="View all Crypto offers"
          >
            <span className="featured-krypto__view-all-label featured-krypto__view-all-label--short">
              All
            </span>
            <span className="featured-krypto__view-all-label featured-krypto__view-all-label--long">
              View all
            </span>
          </Link>
        </div>

        {items && visible.length === 0 ? (
          <EmptyState
            title={hasSearch ? 'No matching crypto markets' : 'No crypto markets'}
            hint={hasSearch ? 'Try another keyword or clear your search.' : 'There are no open rounds right now — check back soon.'}
          />
        ) : (
          <div className="featured-krypto__grid">
            {visible.map((bet) => (
              <KryptoBetCard key={bet.id} {...bet} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default FeaturedKrypto;
