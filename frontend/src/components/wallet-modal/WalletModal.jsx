import React, { useEffect, useState } from 'react';
import '../auth-modal/AuthModal.css';
import './WalletModal.css';
const DISCORD_INVITE = 'https://discord.gg/B4hCCcvG';
const DISCORD_INVITE_LABEL = 'discord.gg/B4hCCcvG';
const TELEGRAM_URL = 'https://t.me/czutkabetcom_bot';
const TELEGRAM_LABEL = 't.me/czutkabetcom_bot';

/** @param {{ open: boolean; onClose: () => void }} props */
function WalletModal({ open, onClose }) {
  const [provider, setProvider] = useState('discord');

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose]);

  useEffect(() => {
    if (open) setProvider('discord');
  }, [open]);

  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  };

  if (!open) return null;

  return (
    <div className="auth-modal__backdrop" role="presentation" onClick={onClose}>
      <div
        className="auth-modal auth-modal--login"
        role="dialog"
        aria-modal="true"
        aria-labelledby="wallet-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button type="button" className="auth-modal__close" aria-label="Close" onClick={onClose} />

        <h2 id="wallet-modal-title" className="auth-modal__headline auth-modal__headline--login">
          Wallet
        </h2>
        <p className="auth-modal__intro auth-modal__intro--login">Deposits and withdrawals via</p>

        <div className="auth-modal__toggle auth-modal__toggle--login" role="tablist" aria-label="Channel">
          <button
            type="button"
            role="tab"
            aria-selected={provider === 'discord'}
            className={
              provider === 'discord'
                ? 'auth-modal__toggle-btn auth-modal__toggle-btn--login auth-modal__toggle-btn--on-login'
                : 'auth-modal__toggle-btn auth-modal__toggle-btn--login'
            }
            onClick={() => setProvider('discord')}
          >
            Discord
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={provider === 'telegram'}
            className={
              provider === 'telegram'
                ? 'auth-modal__toggle-btn auth-modal__toggle-btn--login auth-modal__toggle-btn--on-login'
                : 'auth-modal__toggle-btn auth-modal__toggle-btn--login'
            }
            onClick={() => setProvider('telegram')}
          >
            Telegram
          </button>
        </div>

        {provider === 'discord' ? (
          <>
            <div className="auth-modal__step">
              <p className="auth-modal__step-label">Step 1</p>
              <p className="auth-modal__step-title">Join our server</p>
            </div>

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

            <p className="wallet-modal__body">
              In the Discord bot channel, click <span className="wallet-modal__kbd">Deposit</span> to add funds or{' '}
              <span className="wallet-modal__kbd">Withdraw</span> to cash out — the bot will guide you through the rest.
            </p>
            <p className="auth-modal__channel-note">in the channel</p>
            <p className="auth-modal__channel-note">Use the bot buttons in the channel</p>
          </>
        ) : (
          <>
            <div className="auth-modal__step">
              <p className="auth-modal__step-label">Step 1</p>
              <p className="auth-modal__step-title">Open our Telegram bot</p>
            </div>

            <div className="auth-modal__action-bar">
              <span className="auth-modal__action-text">{TELEGRAM_LABEL}</span>
              <a
                className="auth-modal__action-cta"
                href={TELEGRAM_URL}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open
              </a>
            </div>

            <div className="auth-modal__step-block auth-modal__step-block--spacing">
              <p className="auth-modal__step-label auth-modal__step-label--login">Commands</p>
              <p className="auth-modal__step-title auth-modal__step-title--login">
                Type in the Telegram chat
              </p>
            </div>

            <div className="wallet-modal__cmd-stack">
              <div className="auth-modal__cmd-bar auth-modal__cmd-bar--login">
                <span className="auth-modal__cmd-text">/deposit</span>
                <button type="button" className="auth-modal__cmd-copy" onClick={() => copy('/deposit')}>
                  Copy
                </button>
              </div>
              <div className="auth-modal__cmd-bar auth-modal__cmd-bar--login">
                <span className="auth-modal__cmd-text">/withdraw</span>
                <button type="button" className="auth-modal__cmd-copy" onClick={() => copy('/withdraw')}>
                  Copy
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default WalletModal;
