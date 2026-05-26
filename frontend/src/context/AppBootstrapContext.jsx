import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useLocation } from 'react-router-dom';
import { bootstrapForRoute } from '../lib/appBootstrap';
import { site } from '../lib/api';

const AppBootstrapContext = createContext(null);
const SITE_STATUS_POLL_MS = 15_000;

export function AppBootstrapProvider({ children }) {
  const { pathname } = useLocation();
  const initialPath = useRef(pathname);
  const [ready, setReady] = useState(false);
  const [session, setSession] = useState(null);
  const [siteUnavailable, setSiteUnavailable] = useState(false);

  useEffect(() => {
    let alive = true;

    bootstrapForRoute(initialPath.current)
      .then(({ session: s, siteUnavailable: down }) => {
        if (!alive) return;
        setSession(s);
        setSiteUnavailable(Boolean(down));
        setReady(true);
      })
      .catch(() => {
        if (!alive) return;
        setSession(null);
        setSiteUnavailable(false);
        setReady(true);
      });

    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (pathname.startsWith('/admin')) return undefined;

    let alive = true;
    const poll = () => {
      site
        .getSiteStatus()
        .then((s) => {
          if (!alive) return;
          setSiteUnavailable(Boolean(s?.siteUnavailable));
        })
        .catch(() => {});
    };

    poll();
    const id = window.setInterval(poll, SITE_STATUS_POLL_MS);
    return () => {
      alive = false;
      window.clearInterval(id);
    };
  }, [pathname]);

  const value = useMemo(
    () => ({ ready, session, siteUnavailable }),
    [ready, session, siteUnavailable],
  );

  return (
    <AppBootstrapContext.Provider value={value}>
      {children}
    </AppBootstrapContext.Provider>
  );
}

export function useAppBootstrap() {
  const ctx = useContext(AppBootstrapContext);
  if (!ctx) {
    throw new Error('useAppBootstrap must be used within AppBootstrapProvider');
  }
  return ctx;
}
