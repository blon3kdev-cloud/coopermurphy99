import React, { useEffect, useState } from 'react';
import { chipUrl } from '../../lib/assets';
import { stripCurrencySuffix } from '../../lib/currencyFormat';
import { BetCardRow, BetTicketCluster } from '../bet-ticket/BetTicket';
import ShareBetModal from '../share-bet-sheet/ShareBetModal';
import './WinModal.css';

function ShareIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
      <path
        d="M3 11L11 3M11 3H5.5M11 3V8.5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

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
 *   totalWin?: string;
 *   bets?: object[];
 *   isParlay?: boolean;
 * }} props
 */
function WinModal({
  open = false,
  onClose,
  totalWin = '',
  bets = [],
  isParlay = false,
}) {
  const [shareOpen, setShareOpen] = useState(false);
  const slipBets = bets?.length ? bets : [];

  useEffect(() => {
    if (!open || shareOpen) return undefined;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, onClose, shareOpen]);

  useEffect(() => {
    if (!open) setShareOpen(false);
  }, [open]);

  if (!open || !slipBets.length) return null;

  const handleClose = () => onClose?.();
  const displayBet = slipBets[slipBets.length - 1];

  if (shareOpen) {
    return (
      <ShareBetModal
        open
        bet={displayBet}
        bets={slipBets}
        totalWin={totalWin}
        showBack
        onBack={() => setShareOpen(false)}
        onClose={handleClose}
      />
    );
  }

  return (
    <div className="win-modal__backdrop" role="presentation">
      <div className="win-modal__shell">
        <div className="win-modal__actions" data-node-id="172:355">
          <button type="button" className="win-modal__share" onClick={() => setShareOpen(true)}>
            Udostępnij <ShareIcon />
          </button>
          <button type="button" className="win-modal__dismiss" onClick={handleClose}>
            Zamknij <CloseIcon />
          </button>
        </div>

        <div className="win-modal__frame" data-node-id="172:338">
          <div className="win-modal__card-wrap">
            <div className="win-modal__rings" aria-hidden>
              <span className="win-modal__ring" />
              <span className="win-modal__ring" />
            </div>
            <div className="win-modal__panel" data-node-id="172:334">
              <header className="win-modal__header" data-node-id="172:350">
                <h2 id="win-modal-title" className="win-modal__title">
                  Gratulacje! Wygrałeś
                </h2>
                <div className="win-modal__amount-row">
                  <span className="win-modal__amount">
                    {stripCurrencySuffix(totalWin)}
                  </span>
                  <img src={chipUrl} alt="" className="win-modal__amount-chip" />
                </div>
              </header>

              <div className="win-modal__ticket-wrap">
                <div className="win-modal__ticket">
                  {isParlay && slipBets.length > 1 ? (
                    <BetTicketCluster
                      bets={slipBets}
                      isParlay
                      showFullStats
                      ended
                      showCostChip={false}
                      statLabels={{
                        multiplier: 'mnożnik',
                        multiplierTotal: 'Mnożnik łączny',
                        cost: 'koszt',
                        win: 'wygrana',
                      }}
                    />
                  ) : (
                    <BetCardRow
                      bet={displayBet}
                      showFullStats
                      hideShare
                      showCostChip={false}
                      className="yb__card--win-modal"
                      statLabels={{
                        multiplier: 'mnożnik',
                        multiplierTotal: 'Mnożnik łączny',
                        cost: 'koszt',
                        win: 'wygrana',
                      }}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default WinModal;
