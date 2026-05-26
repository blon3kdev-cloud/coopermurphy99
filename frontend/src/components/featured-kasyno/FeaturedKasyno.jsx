import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useCursorTilt } from '../../hooks/useCursorTilt';
import EmptyState from '../empty-state/EmptyState';
import { filterCasinoGames } from '../../lib/marketFilters';
import { buildFeaturedKasynoGames } from '../../lib/kasynoGames';
import './FeaturedKasyno.css';
import {
  kenoUrl as IMG_KENO,
  limboUrl as IMG_LIMBO,
  diceUrl as IMG_DICE,
  crashUrl as IMG_CRASH,
  blackjack21Url,
  blitzUrl,
  dice2Url,
} from '../../lib/assets';

const FEATURED_IMAGES = {
  keno: IMG_KENO,
  limbo: IMG_LIMBO,
  dice: IMG_DICE,
  crash: IMG_CRASH,
  blackjack21: blackjack21Url,
  blitz: blitzUrl,
  dice2: dice2Url,
};

function KasynoFeaturedCard({ title, image, to }) {
  const tilt = useCursorTilt();
  return (
    <Link className="featured-kasyno__card" to={to} aria-label={title}>
      <span className="featured-kasyno__card-tilt" {...tilt}>
        {image ? (
          <img alt={title} className="featured-kasyno__img" src={image} />
        ) : (
          <span className="featured-kasyno__placeholder">{title}</span>
        )}
      </span>
    </Link>
  );
}

function FeaturedKasyno({ query = '' }) {
  const featured = useMemo(() => buildFeaturedKasynoGames(), []);
  const visible = useMemo(
    () => filterCasinoGames(featured, query),
    [featured, query],
  );
  const hasSearch = Boolean(String(query || '').trim());

  return (
    <section className="featured-kasyno" aria-labelledby="featured-kasyno-heading">
      <div className="featured-kasyno__inner">
        <div className="featured-kasyno__header">
          <h2 id="featured-kasyno-heading" className="featured-kasyno__heading">
            Featured casino
          </h2>
          <Link
            className="featured-kasyno__view-all"
            to="/casino"
            aria-label="View all casino games"
          >
            <span className="featured-kasyno__view-all-label featured-kasyno__view-all-label--short">
              All
            </span>
            <span className="featured-kasyno__view-all-label featured-kasyno__view-all-label--long">
              View all
            </span>
          </Link>
        </div>

        {visible.length === 0 ? (
          <EmptyState
            title={hasSearch ? 'No matching casino games' : 'No casino games'}
            hint={hasSearch ? 'Try another keyword or clear your search.' : undefined}
          />
        ) : (
          <ul className="featured-kasyno__row">
            {visible.map((g) => (
              <li key={g.slug} className="featured-kasyno__item">
                <KasynoFeaturedCard
                  title={g.featuredTitle}
                  image={FEATURED_IMAGES[g.slug] ?? null}
                  to={`/casino/${g.slug}`}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

export default FeaturedKasyno;
