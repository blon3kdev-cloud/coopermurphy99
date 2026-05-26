import React from 'react';
import { stripCurrencySuffix } from '../../lib/currencyFormat';
import { chipUrl } from '../../lib/assets';
import btcIcon from '../../assets/btc.svg';
import ethIcon from '../../assets/eth.svg';
import solIcon from '../../assets/sol.svg';
import usdcIcon from '../../assets/usdc.svg';
import { safeImageUrl } from '../../lib/safeUrl';
import './BetTicket.css';

const CRYPTO_ICONS = { btc: btcIcon, eth: ethIcon, sol: solIcon, usdc: usdcIcon };

function cryptoIcon(symbol) {
  return CRYPTO_ICONS[String(symbol || '').toLowerCase()] || usdcIcon;
}

/** Sizes the page grid column to match the share button beside tickets. */
export function ShareColumnSpacer() {
  return (
    <div className="yb__col-spacer" aria-hidden>
      <span className="yb__share-btn yb__col-spacer__btn">
        Udostępnij <ShareIcon />
      </span>
    </div>
  );
}

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

function ZigzagEdge() {
  return <div className="yb__zigzag" aria-hidden />;
}

function BetThumb({ bet }) {
  if (bet.symbol) {
    return (
      <img
        src={cryptoIcon(bet.symbol)}
        alt=""
        className="yb__card-thumb yb__card-thumb--img"
        decoding="async"
      />
    );
  }
  const imgSrc = safeImageUrl(bet.image);
  if (imgSrc) {
    return (
      <img
        src={imgSrc}
        alt=""
        className="yb__card-thumb yb__card-thumb--img"
        decoding="async"
      />
    );
  }
  return <div className="yb__card-thumb" aria-hidden />;
}

function parlayCardClass(index, total, isParlay) {
  if (!isParlay || total <= 1) return '';
  if (index === 0) return 'yb__card--stack-first';
  if (index === total - 1) return 'yb__card--stack-last';
  return 'yb__card--stack-mid';
}

function parseOddsMultiplier(multStr) {
  const n = parseFloat(
    String(multStr || '')
      .replace(/x$/i, '')
      .trim()
      .replace(',', '.'),
  );
  return Number.isFinite(n) && n > 0 ? n : 1;
}

export function formatCombinedMultiplier(bets) {
  const combined = (bets ?? []).reduce(
    (acc, b) => acc * parseOddsMultiplier(b.multiplier),
    1,
  );
  return `${combined.toFixed(2)}x`;
}

export function BetCardRow({
  bet,
  showFullStats,
  ended = false,
  hideShare = false,
  onShare,
  showCostChip = true,
  showZigzag = true,
  combinedMultiplier = null,
  hideDivider = false,
  statLabels,
  className = '',
}) {
  const labels = {
    multiplier: 'multiplier',
    multiplierTotal: 'Multiplier total',
    cost: 'cost',
    win: ended ? 'Your winnings' : 'potential win',
    ...statLabels,
  };
  const showStatsBlock = showFullStats || Boolean(combinedMultiplier);
  return (
    <>
      {!hideShare && (
        <button
          type="button"
          className="yb__share-btn"
          aria-label="Udostępnij"
          onClick={() => onShare?.(bet)}
        >
          Udostępnij <ShareIcon />
        </button>
      )}

      <div className={`yb__card${className ? ` ${className}` : ''}`}>
        <div className="yb__card-header">
          <div className="yb__card-meta">
            <p className="yb__card-title">{bet.title}</p>
            <p className="yb__card-answer">{bet.answer}</p>
            {bet.eventDate && (
              <p className="yb__card-date">{bet.eventDate}</p>
            )}
          </div>
          <BetThumb bet={bet} />
        </div>

        {!hideDivider && <div className="yb__card-divider" />}

        {showStatsBlock && (
        <div className="yb__card-stats">
          <div className="yb__stat-row">
            <span className="yb__stat-label">
              {combinedMultiplier ? labels.multiplierTotal : labels.multiplier}
            </span>
            <span className="yb__stat-value">
              {combinedMultiplier ?? bet.multiplier}
            </span>
          </div>

          {showFullStats && bet.cost && (
            <div className="yb__stat-row">
              <span className="yb__stat-label">{labels.cost}</span>
              <span className="yb__stat-win-wrap">
                <span className="yb__stat-value">
                  {showCostChip ? stripCurrencySuffix(bet.cost) : bet.cost}
                </span>
                {showCostChip && (
                  <img src={chipUrl} alt="" className="yb__stat-chip" />
                )}
              </span>
            </div>
          )}

          {showFullStats && bet.potWin && (
            <div className="yb__stat-row">
              <span className="yb__stat-label">{labels.win}</span>
              <span className="yb__stat-win-wrap">
                <span className="yb__stat-win">{stripCurrencySuffix(bet.potWin)}</span>
                <img src={chipUrl} alt="" className="yb__stat-chip" />
              </span>
            </div>
          )}
        </div>
        )}

        {showZigzag && <ZigzagEdge />}
      </div>
    </>
  );
}

export function BetTicketCluster({
  bets,
  isParlay = false,
  showFullStats = true,
  ended = false,
  onShare,
  statLabels,
  showCostChip = true,
}) {
  const parlayStack = isParlay && bets.length > 1;
  const combinedMultiplier = parlayStack ? formatCombinedMultiplier(bets) : null;

  return (
    <div
      className={`yb__ticket-cluster${parlayStack ? ' yb__ticket-cluster--parlay' : ''}`}
    >
      {onShare && (
        <button
          type="button"
          className="yb__share-btn"
          aria-label="Udostępnij"
          onClick={() => onShare(bets)}
        >
          Udostępnij <ShareIcon />
        </button>
      )}

      <div className="yb__ticket-stack">
        {bets.map((bet, index) => {
          const isLast = index === bets.length - 1;
          return (
          <BetCardRow
            key={bet.id}
            bet={bet}
            hideShare
            showFullStats={showFullStats && (!parlayStack || isLast)}
            ended={ended}
            className={parlayCardClass(index, bets.length, parlayStack)}
            showZigzag={!parlayStack || isLast}
            hideDivider={parlayStack && !isLast}
            combinedMultiplier={parlayStack && isLast ? combinedMultiplier : null}
            statLabels={statLabels}
            showCostChip={showCostChip}
          />
          );
        })}
      </div>
    </div>
  );
}

