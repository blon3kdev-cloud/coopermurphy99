import { Navigate, useLocation, useParams } from 'react-router-dom';

/** Preserve path suffix, query, and hash when redirecting old Polish slugs. */
export function LegacyPrefixRedirect({ from, to }) {
  const { pathname, search, hash } = useLocation();
  const suffix = pathname.startsWith(from) ? pathname.slice(from.length) : '';
  return <Navigate to={`${to}${suffix}${search}${hash}`} replace />;
}

export function LegacyCasinoGameRedirect() {
  const { gameSlug } = useParams();
  const target = gameSlug ? `/casino/${gameSlug}` : '/casino';
  return <Navigate to={target} replace />;
}
