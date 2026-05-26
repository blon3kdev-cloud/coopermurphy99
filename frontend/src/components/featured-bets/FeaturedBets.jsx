import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useCursorTilt } from '../../hooks/useCursorTilt';
import { useBetSlip } from '../../context/BetSlipContext';
import EmptyState from '../empty-state/EmptyState';
import { markets } from '../../lib/api';
import { getCached, subscribeCached } from '../../lib/apiCache';
import { filterMarkets } from '../../lib/marketFilters';
import { marketDisplayTitle } from '../../lib/marketDisplay';
import { safeImageUrl } from '../../lib/safeUrl';
import './FeaturedBets.css';

export function FeaturedBetCard({ market }) {
  const tilt = useCursorTilt();
  const { addMarketBet, bets } = useBetSlip();
  const {
    image,
    date,
    yesOdds,
    noOdds,
    yesLabel = 'Yes',
    noLabel = 'No',
  } = market;

  const displayTitle = marketDisplayTitle(market);
  const slipSide = bets.find((b) => b.betId === `market-${market.id}`)?.selectedSide ?? null;
  const onCardActivate = () => addMarketBet(market);

  return (
    <article
      className="featured-bets__card"
      {...tilt}
      role="button"
      tabIndex={0}
      onClick={onCardActivate}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onCardActivate();
        }
      }}
    >
      <div className="featured-bets__media">
        {safeImageUrl(image) ? (
          <img alt="" className="featured-bets__media-img" src={safeImageUrl(image)} />
        ) : null}
        <div className="featured-bets__media-shade" aria-hidden="true" />
        {date ? (
          <span className="featured-bets__date-badge" title={date}>{date}</span>
        ) : null}
      </div>
      <div className="featured-bets__body">
        <div className="featured-bets__meta">
          <h3 className="featured-bets__title" title={displayTitle}>{displayTitle}</h3>
        </div>
        <div className="featured-bets__actions">
          <button
            type="button"
            className={`featured-bets__btn featured-bets__btn--yes${slipSide === 'yes' ? ' featured-bets__btn--selected' : ''}`}
            aria-label={`${yesLabel}, ${yesOdds}`}
            onClick={(e) => { e.stopPropagation(); addMarketBet(market, 'yes'); }}
          >
            <span className="featured-bets__btn-label">{yesLabel}</span>
            <span className="featured-bets__btn-odds">{yesOdds}</span>
          </button>
          <button
            type="button"
            className={`featured-bets__btn featured-bets__btn--no${slipSide === 'no' ? ' featured-bets__btn--selected' : ''}`}
            aria-label={`${noLabel}, ${noOdds}`}
            onClick={(e) => { e.stopPropagation(); addMarketBet(market, 'no'); }}
          >
            <span className="featured-bets__btn-label">{noLabel}</span>
            <span className="featured-bets__btn-odds">{noOdds}</span>
          </button>
        </div>
      </div>
    </article>
  );
}

function FeaturedBets({ query = '' }) {
  const cached = getCached('markets:featured');
  const [items, setItems] = useState(() => (Array.isArray(cached) ? cached : null));
  const visible = useMemo(
    () => filterMarkets(items ?? [], { categoryId: '', query }),
    [items, query],
  );
  const hasSearch = Boolean(String(query || '').trim());

  useEffect(() => {
    return subscribeCached(
      'markets:featured',
      () => markets.listFeatured(),
      (data) => setItems(Array.isArray(data) ? data : []),
      30_000,
    );
  }, []);

  return (
    <section className="featured-bets" aria-labelledby="featured-bets-heading">
      <div className="featured-bets__inner">
        <div className="featured-bets__header">
          <h2 id="featured-bets-heading" className="featured-bets__heading">
            Most popular bets
          </h2>
          <Link
            className="featured-bets__view-all"
            to="/bets"
            aria-label="View all bets"
          >
            <span className="featured-bets__view-all-label featured-bets__view-all-label--short">
              All
            </span>
            <span className="featured-bets__view-all-label featured-bets__view-all-label--long">
              View all
            </span>
          </Link>
        </div>

        {items && visible.length === 0 ? (
          <EmptyState
            title={hasSearch ? 'No matching bets' : 'No bets to show'}
            hint={hasSearch ? 'Try another keyword or clear your search.' : 'Check back soon — new markets are on the way.'}
          />
        ) : (
          <div className="featured-bets__grid">
            {visible.map((c) => (
              <FeaturedBetCard key={c.id} market={c} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

export default FeaturedBets;
