import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import './AuthModal.css';
import { auth } from '../../lib/api';
import { DiscordIcon, TelegramIcon } from './AuthProviderIcons';

const DISCORD_INVITE = 'https://discord.gg/B4hCCcvG';
const DISCORD_INVITE_LABEL = 'discord.gg/B4hCCcvG';
const TELEGRAM_URL = 'https://t.me/czutkabetcom_bot';
const TELEGRAM_LABEL = 't.me/czutkabetcom_bot';
const OTP_LENGTH = 6;
const IS_LOCAL_DEV = process.env.NODE_ENV === 'development';
const EMPTY_OTP = () => Array.from({ length: OTP_LENGTH }, () => '');

/** @param {{ active: boolean; loginVariant?: boolean; onSelect: () => void; icon: React.ReactNode; label: string }} props */
function ProviderTab({ active, loginVariant, onSelect, icon, label }) {
  const btnClass = loginVariant
    ? active
      ? 'auth-modal__toggle-btn auth-modal__toggle-btn--login auth-modal__toggle-btn--on-login'
      : 'auth-modal__toggle-btn auth-modal__toggle-btn--login'
    : active
      ? 'auth-modal__toggle-btn auth-modal__toggle-btn--on'
      : 'auth-modal__toggle-btn';
  const iconClass = loginVariant
    ? 'auth-modal__toggle-icon auth-modal__toggle-icon--login'
    : 'auth-modal__toggle-icon';

  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      className={btnClass}
      onClick={onSelect}
    >
      {icon}
      {label}
    </button>
  );
}

/** @param {{ provider: 'discord' | 'telegram'; loginVariant?: boolean; onDiscord: () => void; onTelegram: () => void }} props */
function ProviderToggle({ provider, loginVariant, onDiscord, onTelegram }) {
  const toggleClass = loginVariant ? 'auth-modal__toggle auth-modal__toggle--login' : 'auth-modal__toggle';
  const iconClass = loginVariant
    ? 'auth-modal__toggle-icon auth-modal__toggle-icon--login'
    : 'auth-modal__toggle-icon';

  return (
    <div className={toggleClass} role="tablist" aria-label={loginVariant ? 'Login method' : 'Sign-up method'}>
      <ProviderTab
        active={provider === 'discord'}
        loginVariant={loginVariant}
        onSelect={onDiscord}
        icon={<DiscordIcon className={iconClass} />}
        label="Discord"
      />
      <ProviderTab
        active={provider === 'telegram'}
        loginVariant={loginVariant}
        onSelect={onTelegram}
        icon={<TelegramIcon className={iconClass} />}
        label="Telegram"
      />
    </div>
  );
}

/** @param {{ loginVariant?: boolean; label: string; title: string; spacing?: boolean }} props */
function StepBlock({ loginVariant, label, title, spacing }) {
  const blockClass = spacing
    ? 'auth-modal__step-block auth-modal__step-block--spacing'
    : 'auth-modal__step-block';
  const labelClass = loginVariant ? 'auth-modal__step-label auth-modal__step-label--login' : 'auth-modal__step-label';
  const titleClass = loginVariant ? 'auth-modal__step-title auth-modal__step-title--login' : 'auth-modal__step-title';

  return (
    <div className={blockClass}>
      <p className={labelClass}>{label}</p>
      <p className={titleClass}>{title}</p>
    </div>
  );
}

/** @param {{ mode: 'register' | 'login' | null; onClose: () => void; onSwitchMode: (mode: 'register' | 'login') => void; onLoggedIn?: (session: { username: string; balance: string }) => void }} props */
function AuthModal({ mode, onClose, onSwitchMode, onLoggedIn }) {
  const [provider, setProvider] = useState('discord');
  const [otp, setOtp] = useState(() => /** @type {string[]} */ (EMPTY_OTP()));
  const [authError, setAuthError] = useState('');
  const [codeBusy, setCodeBusy] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const otpRefs = useRef(
    /** @type {(HTMLInputElement | null)[]} */ (Array.from({ length: OTP_LENGTH }, () => null)),
  );

  useEffect(() => {
    if (!mode) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [mode, onClose]);

  useEffect(() => {
    if (mode) {
      setProvider('discord');
      setOtp(EMPTY_OTP());
      setAuthError('');
      setTermsAccepted(false);
    }
  }, [mode]);

  const copyCommand = async (cmd) => {
    try {
      await navigator.clipboard.writeText(cmd);
    } catch {
      /* ignore */
    }
  };

  /** @param {string[]} next */
  const finishLogin = (session) => {
    if (session?.username) {
      try { window.dispatchEvent(new Event('czutka-auth')); } catch {}
    }
    onLoggedIn?.({
      username: session?.username ?? 'username',
      balance: session?.balance ?? '—',
    });
  };

  const resetCode = () => {
    setOtp(EMPTY_OTP());
    otpRefs.current[0]?.focus();
  };

  const submitCode = async (raw) => {
    const code = raw.replace(/\s/g, '');
    if (!code || codeBusy) return;

    if (mode === 'login' && !termsAccepted) {
      setAuthError('Please confirm that you are 18+ and accept our Terms and Privacy Policy.');
      return;
    }

    setAuthError('');
    setCodeBusy(true);
    try {
      // Dev code is often 6 digits — try dev login first so it is not treated as OTP only.
      if (mode === 'login' && IS_LOCAL_DEV) {
        try {
          const session = await auth.devLogin(code);
          finishLogin(session);
          return;
        } catch (err) {
          if (err?.status !== 404 && err?.status !== 401) {
            setAuthError(err?.message || 'Invalid code');
            resetCode();
            return;
          }
        }
      }

      if (new RegExp(`^\\d{${OTP_LENGTH}}$`).test(code)) {
        const session = await auth.verifyOtp(provider, code);
        finishLogin(session);
        return;
      }

      setAuthError('Invalid code');
      resetCode();
    } catch (err) {
      setAuthError(err?.message || 'Invalid code');
      resetCode();
    } finally {
      setCodeBusy(false);
    }
  };

  const flushIfComplete = async (next) => {
    if (next.length !== OTP_LENGTH || !next.every((c) => c.length === 1)) return;
    await submitCode(next.join(''));
  };

  /** @param {number} i @param {string} raw */
  const setOtpIndex = (i, raw) => {
    const only = raw.replace(/\s/g, '').slice(-1);
    setOtp((prev) => {
      const next = [...prev];
      next[i] = only;
      flushIfComplete(next);
      return next;
    });
    if (only && i < OTP_LENGTH - 1) otpRefs.current[i + 1]?.focus();
  };

  /** @param {number} i @param {React.KeyboardEvent<HTMLInputElement>} e */
  const onOtpKeyDown = (i, e) => {
    if (e.key === 'Backspace' && !otp[i] && i > 0) otpRefs.current[i - 1]?.focus();
  };

  /** @param {React.ClipboardEvent<HTMLInputElement>} e */
  const onOtpPaste = (e) => {
    e.preventDefault();
    const raw = e.clipboardData.getData('text').replace(/\s/g, '');
    if (!raw) return;

    if (IS_LOCAL_DEV && (raw.length !== OTP_LENGTH || !new RegExp(`^\\d{${OTP_LENGTH}}$`).test(raw))) {
      submitCode(raw);
      return;
    }

    const chars = [...raw].slice(0, OTP_LENGTH);
    const next = EMPTY_OTP();
    chars.forEach((c, idx) => {
      if (idx < OTP_LENGTH) next[idx] = c;
    });
    setOtp(next);
    if (chars.length === OTP_LENGTH) flushIfComplete(next);
    otpRefs.current[Math.min(Math.max(chars.length - 1, 0), OTP_LENGTH - 1)]?.focus();
  };

  if (!mode) return null;

  const modalClass =
    mode === 'login' ? 'auth-modal auth-modal--login' : 'auth-modal';

  const joinDiscordBar = (
    <div className="auth-modal__action-bar">
      <span className="auth-modal__action-text">{DISCORD_INVITE_LABEL}</span>
      <a
        className="auth-modal__action-cta"
        href={DISCORD_INVITE}
        target="_blank"
        rel="noopener noreferrer"
      >
        Join
      </a>
    </div>
  );

  const joinTelegramBar = (
    <div className="auth-modal__action-bar">
      <span className="auth-modal__action-text">{TELEGRAM_LABEL}</span>
      <a
        className="auth-modal__action-cta"
        href={TELEGRAM_URL}
        target="_blank"
        rel="noopener noreferrer"
      >
        Join
      </a>
    </div>
  );

  return (
    <div
      className="auth-modal__backdrop"
      role="presentation"
      onClick={onClose}
    >
      <div
        className={modalClass}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          type="button"
          className="auth-modal__close"
          aria-label="Close"
          onClick={onClose}
        />

        {mode === 'login' ? (
          <>
            <h2 id="auth-modal-title" className="auth-modal__headline auth-modal__headline--login">
              Login
            </h2>

            <ProviderToggle
              provider={provider}
              loginVariant
              onDiscord={() => setProvider('discord')}
              onTelegram={() => setProvider('telegram')}
            />

            {provider === 'discord' ? (
              <>
                <StepBlock loginVariant label="Step 1" title="Join our discord" />
                {joinDiscordBar}
                <StepBlock loginVariant label="Step 2" title="Press Log in (Sign up if not registered yet)" spacing />
              </>
            ) : (
              <>
                <StepBlock loginVariant label="Step 1" title="Open our Telegram bot" />
                {joinTelegramBar}
                <StepBlock loginVariant label="Step 2" title="Type /login (Sign up if not registered yet)" />
                <div className="auth-modal__cmd-bar auth-modal__cmd-bar--login">
                  <span className="auth-modal__cmd-text">/login</span>
                  <button type="button" className="auth-modal__cmd-copy" onClick={() => copyCommand('/login')}>
                    Copy
                  </button>
                </div>
              </>
            )}

            <div className="auth-modal__step-block auth-modal__step-block--spacing">
              <p className="auth-modal__step-title auth-modal__step-title--login">
                Enter the code you received
              </p>
            </div>

            <div className="auth-modal__otp-row">
              {Array.from({ length: OTP_LENGTH }, (_, idx) => idx).map((idx) => (
                <input
                  key={`otp-slot-${idx}`}
                  ref={(el) => {
                    otpRefs.current[idx] = el;
                  }}
                  type="text"
                  inputMode="text"
                  autoComplete="one-time-code"
                  maxLength={1}
                  className="auth-modal__otp-cell"
                  disabled={codeBusy}
                  value={otp[idx]}
                  onChange={(e) => setOtpIndex(idx, e.target.value)}
                  onKeyDown={(e) => onOtpKeyDown(idx, e)}
                  onPaste={onOtpPaste}
                />
              ))}
            </div>

            <label className="auth-modal__terms">
              <input
                type="checkbox"
                className="auth-modal__terms-input"
                checked={termsAccepted}
                onChange={(e) => {
                  setTermsAccepted(e.target.checked);
                  if (e.target.checked) setAuthError('');
                }}
              />
              <span className="auth-modal__terms-check" aria-hidden="true">
                <svg className="auth-modal__terms-check-icon" viewBox="0 0 12 12" fill="none">
                  <path
                    d="M2.5 6L5 8.5L9.5 3.5"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
              <span className="auth-modal__terms-text">
                I am 18+ and accept the{' '}
                <Link className="auth-modal__terms-link" to="/terms" onClick={(e) => e.stopPropagation()}>
                  Terms
                </Link>
                {' '}and{' '}
                <Link className="auth-modal__terms-link" to="/privacy" onClick={(e) => e.stopPropagation()}>
                  Privacy
                </Link>
              </span>
            </label>

            {authError ? (
              <p className="auth-modal__error" role="alert">{authError}</p>
            ) : null}

            <p className="auth-modal__footer-login">
              <span className="auth-modal__footer-login-muted">Don&apos;t have an account yet? </span>
              <button
                type="button"
                className="auth-modal__footer-login-link"
                onClick={() => onSwitchMode('register')}
              >
                Sign up →
              </button>
            </p>
          </>
        ) : (
          <>
            <h2 id="auth-modal-title" className="auth-modal__headline">
              Sign up
            </h2>

            <ProviderToggle
              provider={provider}
              onDiscord={() => setProvider('discord')}
              onTelegram={() => setProvider('telegram')}
            />

            {provider === 'discord' ? (
              <>
                <StepBlock label="Step 1" title="Join our discord" />
                {joinDiscordBar}
                <StepBlock label="Step 2" title="And press Sign up" spacing />
              </>
            ) : (
              <>
                <StepBlock label="Step 1" title="Open our Telegram bot" />
                {joinTelegramBar}
                <StepBlock label="Step 2" title="And type /register" />
                <div className="auth-modal__action-bar">
                  <span className="auth-modal__action-text">/register</span>
                  <button type="button" className="auth-modal__action-cta" onClick={() => copyCommand('/register')}>
                    Copy
                  </button>
                </div>
              </>
            )}

            <p className="auth-modal__footer">
              <span className="auth-modal__footer-muted">Already have an account? </span>
              <button
                type="button"
                className="auth-modal__footer-link"
                onClick={() => onSwitchMode('login')}
              >
                Log in →
              </button>
            </p>
          </>
        )}
      </div>
    </div>
  );
}

export default AuthModal;
