import React, { useMemo, useState } from 'react';
import { buildBetShareUrl, downloadBetShareCard } from '../../lib/shareBet';
import { toastSuccess } from '../../lib/toast';
import './ShareBetSheet.css';

function DownloadIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden>
      <path
        d="M11 2.75v11M11 13.75l-4-4M11 13.75l4-4"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4.125 15.125v2.75h13.75v-2.75"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * @param {{
 *   bet: object;
 *   bets?: object[];
 *   totalWin?: string;
 *   className?: string;
 * }} props
 */
export function ShareBetSheet({ bet, bets, totalWin, className = '' }) {
  const [copied, setCopied] = useState(false);
  const shareUrl = useMemo(
    () => buildBetShareUrl(bet, { winAmount: totalWin }),
    [bet, totalWin],
  );
  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      toastSuccess('Link skopiowany');
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const onDownload = () => {
    void downloadBetShareCard({ bet, bets, totalWin });
  };

  return (
    <div className={`share-bet${className ? ` ${className}` : ''}`}>
      <h2 id="share-bet-title" className="share-bet__title">
        Udostępnij
      </h2>

      <div className="share-bet__actions">
        <button type="button" className="share-bet__action" onClick={onDownload}>
          <span className="share-bet__action-circle share-bet__action-circle--yellow">
            <DownloadIcon />
          </span>
          <span className="share-bet__action-label">Pobierz</span>
        </button>
      </div>

      <div className="share-bet__compound">
        <span className="share-bet__compound-text" title={shareUrl}>
          {shareUrl}
        </span>
        <button type="button" className="share-bet__compound-btn" onClick={copyLink}>
          {copied ? 'Skopiowano' : 'Skopiuj'}
        </button>
      </div>
    </div>
  );
}

export default ShareBetSheet;
