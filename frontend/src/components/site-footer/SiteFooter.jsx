import React from 'react';
import { Link } from 'react-router-dom';
import './SiteFooter.css';
function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="site-footer__top">
          <div className="site-footer__brand">
            <div className="site-footer__brand-row">
              <img alt="" className="site-footer__brand-mark" src="/czutkalogo.png" />
              <span className="site-footer__brand-name">czutkabet</span>
            </div>
            <p className="site-footer__tagline">
              Bet on the edge. Best bets, 0% commission
            </p>
          </div>

          <div className="site-footer__aside">
            <div className="site-footer__meta">
              <span className="site-footer__meta-brand">
                <span className="site-footer__meta-domain">czutkabet.com® 2026</span>
              </span>
              <span className="site-footer__meta-dot" aria-hidden>
                ·
              </span>
              <Link className="site-footer__meta-link" to="/privacy">
                Privacy
              </Link>
              <span className="site-footer__meta-dot" aria-hidden>
                ·
              </span>
              <Link className="site-footer__meta-link" to="/terms">
                Terms
              </Link>
              <span className="site-footer__meta-dot" aria-hidden>
                ·
              </span>
              <Link className="site-footer__meta-link" to="/provably-fair">
                Provably fair
              </Link>
            </div>
          </div>
        </div>

        <div className="site-footer__legal">
          <p className="site-footer__disclaimer">
            Czutkabet is an entertainment simulation. Play credits have no cash value.
            This is not a licensed casino or financial service. Accounts and wallet
            flows use Discord and Telegram bots. See our{' '}
            <Link className="site-footer__disclaimer-a" to="/terms">
              Terms
            </Link>
            ,{' '}
            <Link className="site-footer__disclaimer-a" to="/privacy">
              Privacy Policy
            </Link>
            , and{' '}
            <Link className="site-footer__disclaimer-a" to="/provably-fair">
              Provably Fair
            </Link>
            .
          </p>
        </div>
      </div>
    </footer>
  );
}

export default SiteFooter;
