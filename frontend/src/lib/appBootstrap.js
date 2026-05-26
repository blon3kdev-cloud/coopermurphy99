import { auth, crypto, markets, site } from './api';

function whenWindowLoaded() {
  if (document.readyState === 'complete') return Promise.resolve();
  return new Promise((resolve) => {
    window.addEventListener('load', resolve, { once: true });
  });
}

/** @param {string} pathname */
function normalizePath(pathname) {
  const p = pathname.replace(/\/$/, '') || '/';
  return p;
}

/** @param {string} path */
function routeTasks(path) {
  switch (path) {
    case '/':
      return [
        markets.listFeatured().catch(() => []),
        crypto.listFeatured().catch(() => []),
        import('../pages/Home'),
      ];
    case '/bets':
      return [
        markets.list().catch(() => ({ items: [], nextCursor: null })),
        import('../pages/BetyPage'),
      ];
    case '/crypto':
      return [crypto.list().catch(() => []), import('../pages/KryptoPage')];
    case '/casino':
      return [import('../pages/KasynoPage')];
    case '/your-bets':
      return [import('../pages/TwojeBetyPage')];
    case '/free-rewards':
      return [import('../pages/DarmoweNagrodyPage')];
    case '/privacy':
      return [import('../pages/PrywatnoscPage')];
    case '/terms':
      return [import('../pages/RegulaminPage')];
    case '/provably-fair':
      return [import('../pages/ProvablyFairPage')];
    default:
      if (path.startsWith('/casino/')) {
        return [import('../pages/KasynoPage')];
      }
      if (path.startsWith('/admin')) {
        return [import('../admin/AdminPanel')];
      }
      return [];
  }
}

const BOOT_TIMEOUT_MS = 12_000;

/**
 * Initial app boot: assets, session, route chunk + API data for the landing path.
 * @param {string} pathname
 * @returns {Promise<{ session: object | null, siteUnavailable: boolean }>}
 */
export async function bootstrapForRoute(pathname) {
  const path = normalizePath(pathname);
  const isAdmin = path.startsWith('/admin');
  const sessionPromise = auth.getSession().catch(() => null);
  const siteStatusPromise = isAdmin
    ? Promise.resolve({ siteUnavailable: false })
    : site.getSiteStatus().catch(() => ({ siteUnavailable: false }));

  const boot = Promise.all([
    document.fonts.ready,
    whenWindowLoaded(),
    sessionPromise,
    siteStatusPromise,
    ...routeTasks(path),
  ]);

  const timeout = new Promise((resolve) => {
    window.setTimeout(resolve, BOOT_TIMEOUT_MS);
  });

  await Promise.race([boot, timeout]);
  const session = await sessionPromise;
  const siteStatus = await siteStatusPromise;
  return {
    session: session?.username ? session : null,
    siteUnavailable: Boolean(siteStatus?.siteUnavailable),
  };
}
