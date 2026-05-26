import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import './CookiesBanner.css';
import { acceptCookieConsent, hasCookieConsent } from '../../lib/consentCookies';

function CookiesBanner() {
  const [visible, setVisible] = useState(() => !hasCookieConsent());

  if (!visible) return null;

  const onAccept = () => {
    acceptCookieConsent();
    setVisible(false);
  };

  return (
    <aside className="cookies-banner" role="dialog" aria-label="Cookie notice">
      <p className="cookies-banner__text">
        We use essential cookies to keep you signed in and remember your preferences.{' '}
        <Link className="cookies-banner__link" to="/privacy">
          Privacy Policy
        </Link>
      </p>
      <button type="button" className="cookies-banner__btn" onClick={onAccept}>
        Accept
      </button>
    </aside>
  );
}

export default CookiesBanner;
