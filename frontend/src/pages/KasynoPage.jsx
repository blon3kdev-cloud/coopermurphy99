import React, { useDeferredValue, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ReactComponent as KasynoLockSvg } from '../assets/games/kasyno-lock.svg';
import CategoryPageHeader from '../components/category-page-header/CategoryPageHeader';
import CasinoGame from '../components/casino/CasinoGame';
import MarketSearch from '../components/market-search/MarketSearch';
import EmptyState from '../components/empty-state/EmptyState';
import { filterCasinoGames } from '../lib/marketFilters';
import {
  kenoUrl as kenoThumb,
  limboUrl as limboThumb,
  diceUrl as diceThumb,
  crashUrl as crashThumb,
  blackjack21Url,
  autaUrl,
  blitzUrl,
  hiloUrl,
} from '../lib/assets';
import {
  KASYNO_AVAILABLE,
  KASYNO_COMING_SOON,
  resolveKasynoEngine,
} from '../lib/kasynoGames';
import { useCursorTilt } from '../hooks/useCursorTilt';
import './casino-games.css';

const LOBBY_THUMBS = {
  keno: kenoThumb,
  limbo: limboThumb,
  dice: diceThumb,
  crash: crashThumb,
  blackjack21: blackjack21Url,
  auta: autaUrl,
  blitz: blitzUrl,
  hilo: hiloUrl,
};

const ORIGINALS = KASYNO_AVAILABLE.map((g) => ({
  slug: g.slug,
  title: g.title,
  thumb: LOBBY_THUMBS[g.slug],
}));

const COMING_SOON = KASYNO_COMING_SOON.map((g) => ({
  slug: g.slug,
  title: g.title,
  thumb: LOBBY_THUMBS[g.slug],
}));

function ComingSoonThumbOverlay() {
  return (
    <div className="kasyno-coming-soon" aria-hidden>
      <span className="kasyno-coming-soon__veil" />
      <span className="kasyno-coming-soon__content">
        <KasynoLockSvg className="kasyno-coming-soon__lock" />
        <span className="kasyno-coming-soon__label">coming soon</span>
      </span>
    </div>
  );
}

function KasynoLobbyThumb({ game, disabled, onPick }) {
  const tilt = useCursorTilt();
  const label = disabled ? `${game.title} — coming soon` : game.title;
  const commonImg = (
    <img className="kasyno-thumb-img" src={game.thumb} alt="" decoding="async" />
  );

  if (disabled) {
    return (
      <div
        className="kasyno-thumb-cell kasyno-thumb-cell--disabled"
        role="listitem"
        aria-label={label}
      >
        {commonImg}
        <ComingSoonThumbOverlay />
      </div>
    );
  }

  return (
    <button
      type="button"
      className="kasyno-thumb-cell"
      role="listitem"
      aria-label={label}
      onClick={() => onPick(game.slug)}
    >
      <span className="kasyno-thumb-cell__tilt" {...tilt}>
        {commonImg}
      </span>
    </button>
  );
}

function KasynoPage() {
  const { gameSlug } = useParams();
  const navigate = useNavigate();
  const engine = resolveKasynoEngine(gameSlug);
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);
  const originalsVisible = useMemo(() => {
    const slugs = new Set(filterCasinoGames(KASYNO_AVAILABLE, deferredQuery).map((g) => g.slug));
    return ORIGINALS.filter((g) => slugs.has(g.slug));
  }, [deferredQuery]);
  const comingSoonVisible = useMemo(() => {
    const slugs = new Set(filterCasinoGames(KASYNO_COMING_SOON, deferredQuery).map((g) => g.slug));
    return COMING_SOON.filter((g) => slugs.has(g.slug));
  }, [deferredQuery]);
  const hasSearch = Boolean(String(deferredQuery || '').trim());
  const noMatches = hasSearch && originalsVisible.length === 0 && comingSoonVisible.length === 0;

  useEffect(() => {
    if (gameSlug && !engine) {
      navigate('/casino', { replace: true });
    }
  }, [gameSlug, engine, navigate]);

  if (engine) {
    return (
      <CasinoGame gameType={engine} onBack={() => navigate('/casino')} />
    );
  }

  return (
    <>
      <CategoryPageHeader title="Casino" className="category-page-header--spacious-back" />
      <MarketSearch query={query} onQueryChange={setQuery} />

      <section className="kasyno-lobby" aria-label="Casino games">
        <div className="kasyno-lobby__inner">
          {noMatches ? (
            <EmptyState
              title="No matching casino games"
              hint="Try another keyword or clear your search."
            />
          ) : (
            <>
              {originalsVisible.length > 0 ? (
                <div className="kasyno-thumb-group">
                  <h3 className="kasyno-thumb-group__label">Originals</h3>
                  <div className="kasyno-thumb-group__grid" role="list">
                    {originalsVisible.map((game) => (
                      <KasynoLobbyThumb
                        key={game.slug}
                        game={game}
                        onPick={(slug) => navigate(`/casino/${slug}`)}
                      />
                    ))}
                  </div>
                </div>
              ) : null}

              {comingSoonVisible.length > 0 ? (
                <div className="kasyno-thumb-group">
                  <h3 className="kasyno-thumb-group__label">Coming soon</h3>
                  <div className="kasyno-thumb-group__grid" role="list">
                    {comingSoonVisible.map((game) => (
                      <KasynoLobbyThumb key={game.slug} game={game} disabled />
                    ))}
                  </div>
                </div>
              ) : null}
            </>
          )}
        </div>
      </section>
    </>
  );
}

export default KasynoPage;
