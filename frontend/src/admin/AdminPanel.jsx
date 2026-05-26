import React, { Suspense, lazy, useEffect, useState } from 'react';
import { NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { Icon } from './AdminUI';
import Login from './Login';
import { admin } from '../lib/api';
import { adminLogout, setAdminUnauthorizedHandler } from '../lib/adminAuth';
import './AdminPanel.css';

const Overview = lazy(() => import('./Overview'));
const Users = lazy(() => import('./Users'));
const Transactions = lazy(() => import('./Transactions'));
const BlikPanel = lazy(() => import('./BlikPanel'));
const Bets = lazy(() => import('./Bets').then((m) => ({ default: m.Bets })));
const AddBet = lazy(() => import('./Bets').then((m) => ({ default: m.AddBet })));
const GameSection = lazy(() => import('./GameSection'));
const Presets = lazy(() => import('./Presets'));
const Codes = lazy(() => import('./Codes'));
const Security = lazy(() => import('./Security'));
const NotFoundPage = lazy(() => import('../pages/NotFoundPage'));

function AdminRouteFallback() {
  return (
    <div className="admin__route-loading" aria-live="polite" aria-label="Loading">
      <div className="page-loader__spinner" aria-hidden="true" />
    </div>
  );
}

const NAV = [
  { to: '/admin', label: 'Overview', icon: 'dashboard', end: true },
  { to: '/admin/users', label: 'Users', icon: 'users' },
  { to: '/admin/transactions', label: 'Transactions', icon: 'transactions' },
  { to: '/admin/blik', label: 'BLIK', icon: 'blik' },
  { to: '/admin/bets', label: 'Bets', icon: 'target' },
  { to: '/admin/presets', label: 'Presets', icon: 'image' },
  { to: '/admin/codes', label: 'Codes', icon: 'codes' },
  { to: '/admin/crypto', label: 'Crypto', icon: 'bitcoin' },
  { to: '/admin/casino', label: 'Casino', icon: 'dice' },
  { to: '/admin/security', label: 'Security', icon: 'lock' },
];

export default function AdminPanel() {
  const [authed, setAuthed] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    setAdminUnauthorizedHandler(() => {
      setAuthed(false);
      setChecking(false);
    });
    return () => setAdminUnauthorizedHandler(null);
  }, []);

  useEffect(() => {
    let alive = true;
    setChecking(true);
    admin
      .getStats('today')
      .then(() => {
        if (alive) setAuthed(true);
      })
      .catch(() => {
        if (alive) setAuthed(false);
      })
      .finally(() => {
        if (alive) setChecking(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const logout = async () => {
    await adminLogout();
    setAuthed(false);
  };

  if (checking) {
    return (
      <div className="admin">
        <AdminRouteFallback />
      </div>
    );
  }

  if (!authed) {
    return <Login onLogin={() => setAuthed(true)} />;
  }

  return (
    <div className="admin">
      <aside className="admin__sidebar">
        <nav className="admin__nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                isActive ? 'admin__nav-item admin__nav-item--active' : 'admin__nav-item'
              }
            >
              <Icon name={n.icon} size={18} />
              <span>{n.label}</span>
            </NavLink>
          ))}
        </nav>
        <button type="button" className="admin__nav-item admin__logout" onClick={logout}>
          <Icon name="logout" size={18} />
          <span>Sign out</span>
        </button>
      </aside>
      <main className="admin__main">
        <Suspense fallback={<AdminRouteFallback />}>
          <Routes>
            <Route index element={<Overview />} />
            <Route path="users" element={<Users />} />
            <Route path="transactions" element={<Transactions />} />
            <Route path="blik" element={<BlikPanel />} />
            <Route path="bets" element={<Bets />} />
            <Route path="bets/new" element={<AddBet />} />
            <Route path="presets" element={<Presets />} />
            <Route path="codes" element={<Codes />} />
            <Route path="security" element={<Security />} />
            <Route path="crypto" element={<GameSection variant="krypto" />} />
            <Route path="casino" element={<GameSection variant="kasyno" />} />
            <Route path="krypto" element={<Navigate to="/admin/crypto" replace />} />
            <Route path="kasyno" element={<Navigate to="/admin/casino" replace />} />
            <Route path="*" element={<NotFoundPage title="Not found — admin" />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}
