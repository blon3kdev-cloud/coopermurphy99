import { useState, useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import './App.css';
import Navbar from './components/navbar/Navbar';
import SiteFooter from './components/site-footer/SiteFooter';
import AuthModal from './components/auth-modal/AuthModal';
import WalletModal from './components/wallet-modal/WalletModal';

import { BetSlipProvider } from './context/BetSlipContext';
import BetSlipSidebar from './components/bet-slip-sidebar/BetSlipSidebar';
import AppToaster from './components/toast/AppToaster';
import WinModal from './components/win-modal/WinModal';
import AgeGateModal from './components/consent/AgeGateModal';
import CookiesBanner from './components/consent/CookiesBanner';
import { useWinCelebration } from './hooks/useWinCelebration';
import { auth } from './lib/api';
import { useAppBootstrap } from './context/AppBootstrapContext';
import {
  setLoginOpener,
  setUnauthorizedHandler,
  setUserSessionActive,
} from './lib/betsApi';
import {
  refreshBalance as syncWalletBalance,
  resetWalletCache,
  subscribeWalletCurrency,
} from './lib/walletCurrency';
import { captureReferralFromUrl } from './lib/referral';
import { attachReferralIfNeeded } from './lib/attachReferralIfNeeded';
import { useVisibilityInterval } from './hooks/useVisibilityInterval';
import { formatPlnBalance, parseAmountFromDisplay } from './lib/currencyFormat';

function navbarBalanceDisplay(balance) {
  if (balance == null || balance === '—') return '—';
  const raw = typeof balance === 'number' ? balance : parseAmountFromDisplay(balance);
  return raw != null ? formatPlnBalance(raw) : String(balance);
}

const LEGAL_STANDALONE_PATHS = new Set(['/privacy', '/terms', '/provably-fair']);

function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

function App() {
  const { pathname } = useLocation();
  const { ready: bootReady, session: bootSession } = useAppBootstrap();
  const legalStandalone = LEGAL_STANDALONE_PATHS.has(pathname);

  const [authMode, setAuthMode] = useState(null);
  const [walletOpen, setWalletOpen] = useState(false);
  const [session, setSession] = useState(
    /** @type {{ username: string; balance: string } | null} */ (null),
  );

  useEffect(() => {
    captureReferralFromUrl();
  }, []);

  useEffect(() => {
    setLoginOpener(setAuthMode);
    setUnauthorizedHandler(() => {
      setUserSessionActive(false);
      setSession(null);
      resetWalletCache();
      setAuthMode('login');
    });
    return () => {
      setLoginOpener(null);
      setUnauthorizedHandler(null);
    };
  }, []);

  useEffect(() => {
    if (!bootReady) return undefined;

    if (bootSession?.username) {
      setUserSessionActive(true);
      setSession({
        username: bootSession.username,
        balance: navbarBalanceDisplay(bootSession.balance),
      });
      attachReferralIfNeeded();
      syncWalletBalance();
      return undefined;
    }

    setUserSessionActive(false);
    setSession(null);
    return undefined;
  }, [bootReady, bootSession]);

  useEffect(() => {
    const onAuth = () => {
      auth.getSession().then((s) => {
        if (!s?.username) return;
        setUserSessionActive(true);
        setSession({
          username: s.username,
          balance: navbarBalanceDisplay(s.balance),
        });
        syncWalletBalance();
      }).catch(() => {});
    };
    window.addEventListener('czutka-auth', onAuth);
    return () => window.removeEventListener('czutka-auth', onAuth);
  }, []);

  useEffect(() => {
    if (!session?.username) return undefined;
    return subscribeWalletCurrency((state) => {
      if (!state.navbarBalance || state.navbarBalance === '—') return;
      setSession((prev) =>
        prev ? { ...prev, balance: state.navbarBalance } : prev,
      );
    });
  }, [session?.username]);

  useVisibilityInterval(() => syncWalletBalance(), 12_000, Boolean(session?.username));

  const { open: winModalOpen, close: closeWinModal, celebration } = useWinCelebration(
    Boolean(session?.username) && !legalStandalone,
  );

  return (
    <BetSlipProvider>
      <div className={legalStandalone ? 'App App--legal-standalone' : 'App'}>
        <ScrollToTop />
        {!legalStandalone && (
          <>
            <Navbar
              session={session}
              onOpenAuth={setAuthMode}
              onOpenWallet={() => setWalletOpen(true)}
              onLogout={async () => {
                try { await auth.logout(); } catch { /* ignore */ }
                setUserSessionActive(false);
                setSession(null);
                resetWalletCache();
              }}
            />
            <div className="App__navbar-spacer" aria-hidden="true" />
          </>
        )}
        <main
          className={
            legalStandalone ? 'App__main App__main--legal-standalone' : 'App__main'
          }
        >
          <Outlet />
        </main>
        {!legalStandalone && <SiteFooter />}
        <AuthModal
          mode={authMode}
          onClose={() => setAuthMode(null)}
          onSwitchMode={setAuthMode}
          onLoggedIn={async (verified) => {
            setSession({
              username: verified?.username ?? 'username',
              balance: navbarBalanceDisplay(verified?.balance),
            });
            setAuthMode(null);
            await attachReferralIfNeeded();
            syncWalletBalance();
          }}
        />
        <WalletModal open={walletOpen} onClose={() => setWalletOpen(false)} />
        <BetSlipSidebar />
        <WinModal
          open={winModalOpen}
          onClose={closeWinModal}
          totalWin={celebration?.totalWin}
          bets={celebration?.bets}
          isParlay={celebration?.isParlay}
        />
        <AppToaster />
        <AgeGateModal />
        <CookiesBanner />
      </div>
    </BetSlipProvider>
  );
}

export default App;
