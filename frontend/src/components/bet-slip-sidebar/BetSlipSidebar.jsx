import React, { useEffect, useMemo, useState } from 'react';
import { useBetSlip } from '../../context/BetSlipContext';
import { cryptoWindowFromBetId, isCryptoOddsBettable } from '../../lib/cryptoOdds';
import { toastError } from '../../lib/toast';
import { useAllLiveCryptoOdds } from '../../hooks/useAllLiveCryptoOdds';
import { chipUrl } from '../../lib/assets';
import { safeImageUrl } from '../../lib/safeUrl';
import btcIcon from '../../assets/btc.svg';
import ethIcon from '../../assets/eth.svg';
import solIcon from '../../assets/sol.svg';
import usdcIcon from '../../assets/usdc.svg';
import EmptyState from '../empty-state/EmptyState';
import { userBets } from '../../lib/api';
import { openLoginIfGuest } from '../../lib/betsApi';
import { refreshBalance, optimisticBalanceDelta } from '../../lib/walletCurrency';
import { ApiError } from '../../lib/api/client';
import { CurrencyAmount } from '../CurrencyAmount';
import { toast } from 'react-toastify';
import './BetSlipSidebar.css';

const CRYPTO_ICONS = { btc: btcIcon, eth: ethIcon, sol: solIcon, usdc: usdcIcon };

function cryptoIcon(symbol) {
  return CRYPTO_ICONS[String(symbol).toLowerCase()] || usdcIcon;
}

function parseOdds(s) {
  const n = parseFloat(String(s).replace(/x/gi, '').replace(',', '.').trim());
  return Number.isFinite(n) && n > 0 ? n : 1;
}

function fmtOdds(n) {
  return (
    n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + 'x'
  );
}

function cryptoMultForBet(bet, liveByWindow) {
  const win = cryptoWindowFromBetId(bet.betId);
  const o = win ? liveByWindow[win] : null;
  const side = bet.selectedSide === 'down' ? 'down' : 'up';
  const mult = o?.[side];
  return isCryptoOddsBettable(mult) ? mult : null;
}

function cryptoLegBlocked(bet, liveByWindow) {
  return bet.kind === 'crypto' && cryptoMultForBet(bet, liveByWindow) == null;
}

function getBetMult(bet, liveByWindow) {
  if (bet.kind === 'crypto') {
    const m = cryptoMultForBet(bet, liveByWindow);
    return m ?? 0;
  }
  return parseOdds(bet.selectedSide === 'no' ? bet.noOdds : bet.yesOdds);
}

/**
 * Parlay bonus multiplier applied on top of combined base odds.
 *   1 bet  → ×1.00 (no bonus)
 *   2 bets → ×1.20
 *   3 bets → ×1.44  (1.2 × 1.2)
 *   4+ bets → ×1.44 (no further increase)
 */
function getBonusMult(count) {
  if (count <= 1) return 1.0;
  if (count === 2) return 1.2;
  return 1.44;
}

function SideLabel({ bet }) {
  if (bet.kind === 'crypto') return bet.selectedSide === 'down' ? 'Lower' : 'Higher';
  return bet.selectedSide === 'no'
    ? (bet.noLabel ?? 'No')
    : (bet.yesLabel ?? 'Yes');
}

function BetItem({ bet, liveByWindow }) {
  const { removeBet } = useBetSlip();
  const mult = getBetMult(bet, liveByWindow);
  const blocked = cryptoLegBlocked(bet, liveByWindow);

  const thumb =
    bet.kind === 'crypto' ? (
      <img className="bet-slip__item-thumb" src={cryptoIcon(bet.symbol)} alt={bet.name ?? ''} />
    ) : (
      <img className="bet-slip__item-thumb" src={safeImageUrl(bet.image) || ''} alt="" />
    );

  return (
    <div className="bet-slip__item">
      <div className="bet-slip__item-top">
        {thumb}
        <span className="bet-slip__item-label">{bet.title}</span>
        <button
          type="button"
          className="bet-slip__item-remove"
          aria-label="Remove"
          onClick={() => removeBet(bet.betId)}
        >
          ×
        </button>
      </div>
      <div className="bet-slip__item-bottom">
        <span className="bet-slip__item-side">
          <SideLabel bet={bet} />
        </span>
        <span className={`bet-slip__item-odds${blocked ? ' bet-slip__item-odds--blocked' : ''}`}>
          {blocked ? '—' : fmtOdds(mult)}
        </span>
      </div>
    </div>
  );
}

export default function BetSlipSidebar() {
  const { bets, isOpen, stake, setStake, close, removeBet, restoreSlip } = useBetSlip();
  const [placing, setPlacing] = useState(false);
  const [placeError, setPlaceError] = useState('');

  const liveByWindow = useAllLiveCryptoOdds();

  const stakeNum = parseFloat(String(stake).replace(',', '.'));
  const stakeOk  = Number.isFinite(stakeNum) && stakeNum > 0;

  /* combined base odds (product, no bonus) */
  const baseCombined = bets.length > 0
    ? bets.reduce((acc, bet) => acc * getBetMult(bet, liveByWindow), 1)
    : 0;

  /* parlay bonus based on how many bets are in the slip */
  const bonusMult      = getBonusMult(bets.length);
  const effectiveMult  = baseCombined * bonusMult;

  /* upsell: show when adding one more bet unlocks a higher bonus tier */
  const nextBonusMult   = getBonusMult(bets.length + 1);
  const showUpsell      = bets.length > 0 && bets.length < 5 && nextBonusMult > bonusMult;

  const blockedCryptoLegs = bets.filter((b) => cryptoLegBlocked(b, liveByWindow));

  const payout = stakeOk && effectiveMult > 0 && blockedCryptoLegs.length === 0
    ? stakeNum * effectiveMult
    : null;

  const fmtPayout = (n) =>
    n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  /* body scroll lock */
  useEffect(() => {
    if (!isOpen) return undefined;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [isOpen]);

  /* Escape key */
  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') close(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, close]);

  if (bets.length === 0 && !isOpen) return null;

  const open = isOpen;

  const placeSlip = async () => {
    if (placing || !stakeOk || bets.length === 0) return;
    if (openLoginIfGuest()) return;

    const blocked = bets.filter((b) => cryptoLegBlocked(b, liveByWindow));
    if (blocked.length > 0) {
      const msg = 'Odds dropped below the minimum — remove or wait for better quotes.';
      setPlaceError(msg);
      toastError(msg);
      return;
    }

    const snapshot = { bets: [...bets], stake };
    const marketBets = bets.filter((b) => b.kind === 'market');
    const cryptoBets = bets.filter((b) => b.kind === 'crypto');

    setPlacing(true);
    setPlaceError('');

    try {
      const res = await userBets.placeParlay({
        stakePln: stakeNum,
        markets: marketBets.map((b) => ({
          marketId: String(b.betId).replace(/^market-/, ''),
          side: b.selectedSide === 'no' ? 'no' : 'yes',
        })),
        crypto: cryptoBets.map((b) => {
          const id = String(b.betId).replace(/^crypto-/, '');
          return {
            window: id.replace(/^k-btc-/, ''),
            direction: b.selectedSide === 'down' ? 'down' : 'up',
          };
        }),
      });

      optimisticBalanceDelta(-stakeNum);
      snapshot.bets.forEach((b) => removeBet(b.betId));
      setStake('');
      close();

      if (res?.balance != null) {
        await refreshBalance({ PLN: res.balance });
      } else {
        await refreshBalance();
      }
      const legCount = marketBets.length + cryptoBets.length;
      const legsLabel = legCount === 1 ? 'bet' : 'bets';
      toast.success(
        <span className="toast-chip-credit">
          Placed {legCount} {legsLabel} — stake <CurrencyAmount value={stakeNum} size={16} />
        </span>,
        { autoClose: 4000 },
      );
    } catch (err) {
      restoreSlip(snapshot.bets, snapshot.stake, true);
      setPlaceError(err instanceof ApiError ? err.message : 'Could not place bet');
    } finally {
      setPlacing(false);
    }
  };

  return (
    <>
      <div
        className={`bet-slip__backdrop${open ? ' bet-slip__backdrop--open' : ''}`}
        aria-hidden="true"
        onClick={close}
      />
      <aside
        className={`bet-slip__panel${open ? ' bet-slip__panel--open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Your bets"
      >
        <button
          type="button"
          className="bet-slip__close"
          aria-label="Close"
          onClick={(e) => {
            e.stopPropagation();
            close();
          }}
        />
        {/* Header */}
        <header className="bet-slip__header">
          <h2 className="bet-slip__header-title">Your bets</h2>
          {bets.length > 0 && (
            <span className="bet-slip__count-badge">{bets.length}</span>
          )}
        </header>

        {/* Bet list */}
        <div className="bet-slip__scroll">
          {bets.length === 0 ? (
            <EmptyState
              title="Your slip is empty"
              hint="Click any bet to add it here."
              compact
            />
          ) : null}

          {bets.map((bet) => (
            <BetItem key={bet.betId} bet={bet} liveByWindow={liveByWindow} />
          ))}

          {/* Upsell — only when next tier gives a real bonus */}
          {showUpsell && (
            <div className="bet-slip__upsell">
              <p className="bet-slip__upsell-text">
                Add one more bet and get{' '}
                <span className="bet-slip__upsell-accent">BOOSTED multi</span>
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="bet-slip__footer">
          {/* Stake input + combined odds */}
          <div className="bet-slip__stake-row">
            <div className="bet-slip__stake-box">
              <input
                className="bet-slip__stake-input"
                type="text"
                inputMode="decimal"
                autoComplete="off"
                placeholder="0"
                value={stake}
                onChange={(e) => setStake(e.target.value)}
              />
              <img className="bet-slip__stake-chip" src={chipUrl} alt="" />
            </div>

            <div className="bet-slip__odds-box" aria-label="Combined odds">
              <span className="bet-slip__footer-odds-text">
                {effectiveMult > 0 ? fmtOdds(effectiveMult) : '—'}
              </span>
            </div>
          </div>

          {/* Payout */}
          <div className="bet-slip__payout-row">
            <span className="bet-slip__payout-label">Potential win:</span>
            {payout != null ? (
              <>
                <span className="bet-slip__payout-value">{fmtPayout(payout)}</span>
                <img className="bet-slip__payout-chip" src={chipUrl} alt="" />
              </>
            ) : (
              <span className="bet-slip__payout-value bet-slip__payout-value--empty">—</span>
            )}
          </div>

          {placeError ? (
            <p className="bet-slip__error" role="alert">{placeError}</p>
          ) : null}

          {/* Submit */}
          <button
            type="button"
            className={['bet-slip__submit', placing && 'bet-slip__submit--placing'].filter(Boolean).join(' ')}
            disabled={!stakeOk || bets.length === 0 || placing || blockedCryptoLegs.length > 0}
            aria-busy={placing}
            onClick={placeSlip}
          >
            {placing ? 'Placing...' : 'Place bet'}
          </button>
        </footer>
      </aside>
    </>
  );
}
