import React, { useEffect, useMemo, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { MAX_SEARCH_QUERY_LEN, sanitizeSearchQuery } from '../../lib/searchQuery';
import './MarketSearch.css';

const SECTION_TABS = [
  { id: 'home', label: 'Home', path: '/', placeholder: 'Search Home' },
  { id: 'bets', label: 'Bets', path: '/bets', placeholder: 'Search Bets' },
  { id: 'crypto', label: 'Crypto', path: '/crypto', placeholder: 'Search Crypto' },
  { id: 'casino', label: 'Casino', path: '/casino', placeholder: 'Search Casino' },
];

/** Static chips for pages without dynamic market data */
const PAGE_FILTER_CHIPS = {};

function ClearIcon() {
  return (
    <svg
      className="market-search__clear-icon"
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M18 6 6 18M6 6l12 12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      className="market-search__icon"
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M10.5 18a7.5 7.5 0 1 1 0-15 7.5 7.5 0 0 1 0 15Z"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M16.5 16.5 21 21"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MarketSearch({
  filterChips: filterChipsProp,
  activeFilterId: activeFilterIdProp,
  onFilterChange,
  query: queryProp,
  onQueryChange,
}) {
  const location = useLocation();
  const [localQuery, setLocalQuery] = useState('');
  const [localFilterId, setLocalFilterId] = useState('');

  const activeId = useMemo(() => {
    const p = location.pathname;
    if (p.startsWith('/bets')) return 'bets';
    if (p.startsWith('/crypto')) return 'crypto';
    if (p.startsWith('/casino')) return 'casino';
    return 'home';
  }, [location.pathname]);

  const isHomePrimaryNav = location.pathname === '/';
  const isBety = activeId === 'bets';

  const pageFilters = useMemo(() => {
    if (isHomePrimaryNav || activeId === 'casino') return null;
    if (isBety && Array.isArray(filterChipsProp)) return filterChipsProp;
    return PAGE_FILTER_CHIPS[activeId] ?? null;
  }, [isHomePrimaryNav, isBety, filterChipsProp, activeId]);

  const query = onQueryChange ? (queryProp ?? '') : localQuery;
  const setQuery = onQueryChange ?? setLocalQuery;
  const activeFilterId = onFilterChange ? activeFilterIdProp : localFilterId;
  const setActiveFilterId = onFilterChange ?? setLocalFilterId;

  useEffect(() => {
    if (isBety || isHomePrimaryNav) return;
    const next = PAGE_FILTER_CHIPS[activeId];
    if (next?.length) {
      setLocalFilterId((prev) => (next.some((f) => f.id === prev) ? prev : next[0].id));
    }
  }, [location.pathname, activeId, isBety, isHomePrimaryNav]);

  const placeholder = useMemo(
    () => SECTION_TABS.find((t) => t.id === activeId)?.placeholder ?? SECTION_TABS[0].placeholder,
    [activeId],
  );

  const hasQuery = Boolean(String(query || '').trim());

  return (
    <section className="market-search" aria-label="Search">
      <div className="market-search__inner">
        {isHomePrimaryNav ? (
          <nav className="market-search__tabs" aria-label="Sections">
            {SECTION_TABS.map((tab) => (
              <NavLink
                key={tab.id}
                to={tab.path}
                end={tab.path === '/'}
                className={({ isActive }) =>
                  isActive ? 'market-search__tab market-search__tab--active' : 'market-search__tab'
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>
        ) : pageFilters?.length > 0 ? (
          <div className="market-search__tabs" role="tablist" aria-label="Filters">
            {pageFilters.map((chip) => {
              const pressed = chip.id === activeFilterId;
              return (
                <button
                  key={chip.id}
                  type="button"
                  role="tab"
                  aria-selected={pressed}
                  className={pressed ? 'market-search__tab market-search__tab--active' : 'market-search__tab'}
                  onClick={() => setActiveFilterId(chip.id)}
                >
                  {chip.label}
                </button>
              );
            })}
          </div>
        ) : null}

        <div className="market-search__field-shell">
          <label className="market-search__label" htmlFor="market-search-input">
            Search
          </label>
          <div className="market-search__field">
            <SearchIcon />
            <input
              id="market-search-input"
              type="search"
              className="market-search__input"
              placeholder={placeholder}
              value={query}
              maxLength={MAX_SEARCH_QUERY_LEN}
              onChange={(e) => setQuery(sanitizeSearchQuery(e.target.value))}
              autoComplete="off"
              spellCheck={false}
            />
            {hasQuery ? (
              <button
                type="button"
                className="market-search__clear"
                aria-label="Clear search"
                onClick={() => setQuery('')}
              >
                <ClearIcon />
                <span className="market-search__clear-label">Clear</span>
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </section>
  );
}

export default MarketSearch;
