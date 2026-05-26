import { marketDisplayTitle } from './marketDisplay';
import { normalizeSearchQuery } from './searchQuery';

/** True while kickoff is still in the future (uses API eventDate ISO). */
export function isMarketOpenForBetting(market) {
  const raw = market?.eventDate;
  if (!raw) return true;
  const t = Date.parse(raw);
  if (Number.isNaN(t)) return true;
  return t > Date.now();
}

/** Filter chip labels — must match backend market_categories.FILTER_LABELS order. */
export const FILTER_LABELS = {
  pilka: 'Football',
  nba: 'NBA',
  tennis: 'Tenis',
  mlb: 'MLB',
  nfl: 'NFL',
  mma: 'MMA',
  boks: 'Boks',
  esports: 'Esports',
  filmy: 'Movies & TV',
  smieszne: 'Funny',
};

const FILTER_ORDER = Object.keys(FILTER_LABELS);

/** Build chip list: "All" first, then categories present in markets. */
export function filtersFromMarkets(markets) {
  const seen = new Set();
  for (const m of markets.filter(isMarketOpenForBetting)) {
    if (m.categoryId) seen.add(m.categoryId);
  }
  const chips = FILTER_ORDER.filter((id) => seen.has(id)).map((id) => ({
    id,
    label: FILTER_LABELS[id],
  }));
  if (!markets.length) return chips;
  return [{ id: '', label: 'All' }, ...chips];
}

export function filterMarkets(markets, { categoryId, query }) {
  let out = markets.filter(isMarketOpenForBetting);
  if (categoryId) {
    out = out.filter((m) => m.categoryId === categoryId);
  }
  const q = normalizeSearchQuery(query);
  if (!q) return out;
  return out.filter((m) => {
    const hay = [
      m.title,
      m.yesLabel,
      m.noLabel,
      marketDisplayTitle(m),
      m.categoryId,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(q);
  });
}

export function filterCryptoItems(items, query) {
  const q = normalizeSearchQuery(query);
  if (!q) return items ?? [];
  return (items ?? []).filter((item) => {
    const hay = [item.title, item.name, item.symbol]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(q);
  });
}

export function filterCasinoGames(games, query) {
  const q = normalizeSearchQuery(query);
  if (!q) return games ?? [];
  return (games ?? []).filter((g) => {
    const hay = [g.title, g.featuredTitle, g.slug]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(q);
  });
}
