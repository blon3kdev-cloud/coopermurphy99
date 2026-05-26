import React from 'react';
import { useLocation } from 'react-router-dom';
import UnavailablePage from '../pages/UnavailablePage';
import { useAppBootstrap } from '../context/AppBootstrapContext';

export default function SiteMaintenanceGate({ children }) {
  const { pathname } = useLocation();
  const { ready, siteUnavailable } = useAppBootstrap();

  if (pathname.startsWith('/admin')) {
    return children;
  }

  if (!ready) {
    return null;
  }

  if (siteUnavailable) {
    return <UnavailablePage />;
  }

  return children;
}
