import React, { Suspense, lazy } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import './index.css';
import App from './App';
import PageLoader from './components/page-loader/PageLoader';
import { AppBootstrapProvider } from './context/AppBootstrapContext';
import {
  LegacyCasinoGameRedirect,
  LegacyPrefixRedirect,
} from './components/LegacyRouteRedirect';
import SiteMaintenanceGate from './components/SiteMaintenanceGate';

const Home = lazy(() => import('./pages/Home'));
const KasynoPage = lazy(() => import('./pages/KasynoPage'));
const BetyPage = lazy(() => import('./pages/BetyPage'));
const KryptoPage = lazy(() => import('./pages/KryptoPage'));
const TwojeBetyPage = lazy(() => import('./pages/TwojeBetyPage'));
const DarmoweNagrodyPage = lazy(() => import('./pages/DarmoweNagrodyPage'));
const PrywatnoscPage = lazy(() => import('./pages/PrywatnoscPage'));
const RegulaminPage = lazy(() => import('./pages/RegulaminPage'));
const ProvablyFairPage = lazy(() => import('./pages/ProvablyFairPage'));
const BlikConfirmPage = lazy(() => import('./pages/BlikConfirmPage'));
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'));
const AdminPanel = lazy(() => import('./admin/AdminPanel'));

function RouteFallback() {
  return null;
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <BrowserRouter>
      <AppBootstrapProvider>
        <PageLoader>
          <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/admin/*" element={<AdminPanel />} />
            <Route
              path="/blik/confirm/:token"
              element={
                <SiteMaintenanceGate>
                  <BlikConfirmPage />
                </SiteMaintenanceGate>
              }
            />
            <Route
              path="/blik/confirm"
              element={
                <SiteMaintenanceGate>
                  <BlikConfirmPage />
                </SiteMaintenanceGate>
              }
            />
            <Route
              path="/blik/potwierdz/*"
              element={<LegacyPrefixRedirect from="/blik/potwierdz" to="/blik/confirm" />}
            />
            <Route
              element={
                <SiteMaintenanceGate>
                  <App />
                </SiteMaintenanceGate>
              }
            >
              <Route index element={<Home />} />
              <Route path="/casino" element={<KasynoPage />} />
              <Route path="/casino/:gameSlug" element={<KasynoPage />} />
              <Route path="/bets" element={<BetyPage />} />
              <Route path="/crypto" element={<KryptoPage />} />
              <Route path="/your-bets" element={<TwojeBetyPage />} />
              <Route path="/free-rewards" element={<DarmoweNagrodyPage />} />
              <Route path="/privacy" element={<PrywatnoscPage />} />
              <Route path="/terms" element={<RegulaminPage />} />
              <Route path="/provably-fair" element={<ProvablyFairPage />} />
              <Route path="/kasyno" element={<Navigate to="/casino" replace />} />
              <Route path="/kasyno/:gameSlug" element={<LegacyCasinoGameRedirect />} />
              <Route path="/bety" element={<Navigate to="/bets" replace />} />
              <Route path="/krypto" element={<Navigate to="/crypto" replace />} />
              <Route path="/darmowe-nagrody" element={<Navigate to="/free-rewards" replace />} />
              <Route path="/prywatnosc" element={<Navigate to="/privacy" replace />} />
              <Route path="/regulamin" element={<Navigate to="/terms" replace />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
          </Suspense>
        </PageLoader>
      </AppBootstrapProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
