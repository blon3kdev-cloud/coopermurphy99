import React, { useEffect } from 'react';
import { ShareBetSheet } from './ShareBetSheet';
import './ShareBetModal.css';

function CloseIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
      <path
        d="M2 2l8 8M10 2L2 10"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

/**
 * @param {{
 *   open?: boolean;
 *   onClose?: () => void;
 *   onBack?: () => void;
 *   showBack?: boolean;
 *   bet?: object;
 *   bets?: object[];
 *   totalWin?: string;
 * }} props
 */
function ShareBetModal({
  open = false,
  onClose,
  onBack,
  showBack = false,
  bet,
  bets,
  totalWin,
}) {
  useEffect(() => {
    if (!open) return undefined;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => {
      if (e.key !== 'Escape') return;
      if (showBack && onBack) onBack();
      else onClose?.();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose, onBack, showBack]);

  const slipBets = bets?.length ? bets : bet ? [bet] : [];
  if (!open || !slipBets.length) return null;

  const handleDismiss = () => {
    if (showBack && onBack) onBack();
    else onClose?.();
  };

  const handleBackdrop = (e) => {
    if (e.target !== e.currentTarget) return;
    handleDismiss();
  };

  return (
    <div
      className="share-bet-modal__backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-bet-title"
      data-node-id="191:537"
      onClick={handleBackdrop}
    >
      <div className="share-bet-modal__shell" onClick={(e) => e.stopPropagation()}>
        <div className="share-bet-modal__header">
          <button type="button" className="share-bet-modal__dismiss" onClick={handleDismiss}>
            Zamknij <CloseIcon />
          </button>
        </div>
        <div className="share-bet-modal__card">
          <ShareBetSheet bet={slipBets[0]} bets={slipBets} totalWin={totalWin} />
        </div>
      </div>
    </div>
  );
}

export default ShareBetModal;
