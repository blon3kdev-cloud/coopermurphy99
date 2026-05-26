import React, { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { chipUrl } from '../../lib/assets';
import { BrandLogo } from '../brand/BrandLogo';
import './Navbar.css';

const MOBILE_NAV_MQ = '(max-width: 900px)';

function useMobileNavLayout() {
  const [mobile, setMobile] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(MOBILE_NAV_MQ).matches : false,
  );

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_NAV_MQ);
    const onChange = () => setMobile(mq.matches);
    onChange();
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, []);

  return mobile;
}

function NavbarAvatarIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M9.78522 3.18531C10.2789 2.44479 11.11 2 12 2C12.89 2 13.7211 2.44479 14.2148 3.18531L14.5924 3.75182C14.925 4.25061 15.5315 4.49147 16.1157 4.35667L16.4882 4.2707C17.3962 4.06117 18.348 4.33416 19.0069 4.99307C19.6658 5.65197 19.9388 6.60383 19.7293 7.5118L19.6433 7.88434C19.5085 8.46846 19.7494 9.07503 20.2482 9.40755L20.8147 9.78522C21.5552 10.2789 22 11.11 22 12C22 12.89 21.5552 13.7211 20.8147 14.2148L20.2482 14.5924C19.7494 14.925 19.5085 15.5315 19.6433 16.1157L19.7293 16.4882C19.9388 17.3962 19.6658 18.348 19.0069 19.0069C18.348 19.6658 17.3962 19.9388 16.4882 19.7293L16.1157 19.6433C15.5315 19.5085 14.925 19.7494 14.5924 20.2482L14.2148 20.8147C13.7211 21.5552 12.89 22 12 22C11.11 22 10.2789 21.5552 9.78522 20.8147L9.40755 20.2482C9.07503 19.7494 8.46846 19.5085 7.88434 19.6433L7.5118 19.7293C6.60383 19.9388 5.65197 19.6658 4.99307 19.0069C4.33416 18.348 4.06117 17.3962 4.2707 16.4882L4.35667 16.1157C4.49147 15.5315 4.25061 14.925 3.75182 14.5924L3.18531 14.2148C2.44479 13.7211 2 12.89 2 12C2 11.11 2.4448 10.2789 3.18531 9.78522L3.75182 9.40755C4.25061 9.07503 4.49147 8.46846 4.35667 7.88434L4.2707 7.5118C4.06117 6.60383 4.33416 5.65197 4.99307 4.99307C5.65197 4.33416 6.60383 4.06117 7.5118 4.2707L7.88434 4.35667C8.46846 4.49147 9.07503 4.25061 9.40755 3.75182L9.78522 3.18531ZM8.5 12C8.5 10.067 10.067 8.5 12 8.5C13.933 8.5 15.5 10.067 15.5 12C15.5 13.933 13.933 15.5 12 15.5C10.067 15.5 8.5 13.933 8.5 12Z"
        fill="currentColor"
      />
    </svg>
  );
}

/** @param {{ onOpenAuth: (mode: 'register' | 'login') => void; onOpenWallet?: () => void; session: { username: string; balance: string } | null; onLogout: () => void }} props */
function Navbar({ onOpenAuth, onOpenWallet, session, onLogout }) {
  const navigate = useNavigate();
  const mobileNav = useMobileNavLayout();
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef(null);

  useEffect(() => {
    if (!profileOpen) return undefined;
    const onDocMouseDown = (e) => {
      if (!profileRef.current?.contains(e.target)) setProfileOpen(false);
    };
    document.addEventListener('mousedown', onDocMouseDown);
    return () => document.removeEventListener('mousedown', onDocMouseDown);
  }, [profileOpen]);

  return (
    <div className="navbar">
      <div
        className={
          session ? 'navbar__container navbar__container--logged' : 'navbar__container'
        }
      >
        <div className={session ? 'navbar__logged-left' : 'navbar__container__left'}>
          <Link to="/" className="navbar__container__left__h2" aria-label="czutkabet.com — home">
            <BrandLogo size={26} color="#FAFAFA" />
            {!mobileNav && <span className="navbar__brand-text">czutkabet.com</span>}
          </Link>

          {!mobileNav && (
            <NavLink
              to="/free-rewards"
              className={({ isActive }) =>
                ['navbar__reward-link', isActive && 'navbar__reward-link--active'].filter(Boolean).join(' ')
              }
            >
              Free rewards
            </NavLink>
          )}
        </div>

        {session ? (
          <>
            <div className="navbar__logged-center">
              <div className="navbar__pill navbar__pill--balance" title="Balance">
                <span className="navbar__balance-text">{session.balance}</span>
                <img
                  src={chipUrl}
                  alt=""
                  className="navbar__chip-img"
                  decoding="async"
                  draggable={false}
                  aria-hidden
                />
              </div>
              <button
                type="button"
                className="navbar__pill navbar__pill--deposit"
                onClick={() => onOpenWallet?.()}
              >
                Top up
              </button>
            </div>
            <div className="navbar__logged-right">
              {!(mobileNav && session) && (
                <button type="button" className="navbar__pill navbar__pill--bets" onClick={() => navigate('/your-bets')}>
                  Your bets
                </button>
              )}
              <div className="navbar__profile-wrap" ref={profileRef}>
                <button
                  type="button"
                  className="navbar__profile-icon-btn"
                  aria-expanded={profileOpen}
                  aria-haspopup="menu"
                  aria-label="Profile"
                  onClick={() => setProfileOpen((o) => !o)}
                >
                  <NavbarAvatarIcon />
                </button>
                {profileOpen && (
                  <div className="navbar__profile-menu" role="menu">
                    {mobileNav && session && (
                      <>
                        <NavLink
                          to="/free-rewards"
                          role="menuitem"
                          className={({ isActive }) =>
                            [
                              'navbar__profile-menu-item',
                              'navbar__profile-menu-link',
                              isActive && 'navbar__profile-menu-link--active',
                            ]
                              .filter(Boolean)
                              .join(' ')
                          }
                          onClick={() => setProfileOpen(false)}
                        >
                          Free rewards
                        </NavLink>
                        <button
                          type="button"
                          className="navbar__profile-menu-item"
                          role="menuitem"
                          onClick={() => {
                            navigate('/your-bets');
                            setProfileOpen(false);
                          }}
                        >
                          Your bets
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      className="navbar__profile-menu-item"
                      role="menuitem"
                      onClick={() => {
                        onLogout();
                        setProfileOpen(false);
                      }}
                    >
                      Log out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="navbar__container__right">
            {mobileNav && (
              <NavLink
                to="/free-rewards"
                aria-label="Free rewards"
                className={({ isActive }) =>
                  [
                    'navbar__reward-link',
                    'navbar__reward-link--toolbar',
                    isActive && 'navbar__reward-link--active',
                  ]
                    .filter(Boolean)
                    .join(' ')
                }
              >
                Rewards
              </NavLink>
            )}
            <button
              type="button"
              className="navbar__container_right__button button_primary"
              onClick={() => onOpenAuth?.('register')}
            >
              Create account
            </button>
            <button
              type="button"
              className="navbar__container_right__button button_secondary"
              onClick={() => onOpenAuth?.('login')}
            >
              Log in
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default Navbar;
