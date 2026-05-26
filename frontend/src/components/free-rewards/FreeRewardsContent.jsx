import React, { useCallback, useEffect, useState } from 'react';
import { rewards } from '../../lib/api';
import { isUserSessionActive, openAuthIfGuest, openLoginIfGuest } from '../../lib/betsApi';
import { refreshBalance } from '../../lib/walletCurrency';
import { CurrencyAmount } from '../CurrencyAmount';
import { toastChipCredit, toastError } from '../../lib/toast';
import { safeReferralUrl } from '../../lib/safeUrl';
import '../../pages/DarmoweNagrodyPage.css';

const DISCORD_URL = 'https://discord.gg/czutkagg';
const DISCORD_LABEL = 'discord.gg/czutkagg';
const TELEGRAM_URL = 'https://t.me/czutkagg';
const TELEGRAM_LABEL = 't.me/czutkagg';

const DEFAULT_VIP_BONUSES = {
  daily: { status: 'cooldown', countdown: '—' },
  weekly: { status: 'cooldown', countdown: '—' },
  monthly: { status: 'cooldown', countdown: '—' },
  rank: { status: 'locked', requirement: 'Required: Gold' },
};

const DEFAULT_REFERRAL_TIERS = [
  { id: 1, label: 'Tier 1', amount: '50', status: 'progress', countdown: '0/10' },
  { id: 2, label: 'Tier 2', amount: '125', status: 'progress', countdown: '0/50' },
  { id: 3, label: 'Tier 3', amount: '250', status: 'progress', countdown: '0/100' },
  { id: 4, label: 'Tier 4', amount: '500', status: 'progress', countdown: '0/250' },
];

function BonusPill({ bonus, kind, onClaim, guest, onRegister }) {
  if (guest) {
    return (
      <button type="button" className="dn__pill dn__pill--yellow" onClick={onRegister}>
        Register
      </button>
    );
  }

  const b = bonus ?? DEFAULT_VIP_BONUSES[kind] ?? { status: 'cooldown', countdown: '—' };
  const ready = b.status === 'ready';
  const claimed = b.status === 'claimed';
  const label = ready
    ? (b.amountPreview != null ? (
        <span className="dn__claim-preview">
          Claim ~<CurrencyAmount value={b.amountPreview} decimals={0} size={16} />
        </span>
      ) : 'Claim')
    : claimed
      ? 'Claimed'
      : b.countdown ?? b.requirement ?? '—';

  return (
    <button
      type="button"
      className={ready ? 'dn__pill dn__pill--yellow' : 'dn__pill dn__pill--mute'}
      disabled={!ready || claimed}
      onClick={() => ready && onClaim?.(kind)}
    >
      {label}
    </button>
  );
}

function ReferralPill({ tier, onClaim, guest, onRegister }) {
  if (guest) {
    return (
      <button type="button" className="dn__pill dn__pill--yellow" onClick={onRegister}>
        Register
      </button>
    );
  }

  const ready = tier.status === 'ready';
  const claimed = tier.status === 'claimed';
  const label = ready ? 'Claim' : claimed ? 'Claimed' : tier.countdown ?? '—';

  return (
    <button
      type="button"
      className={ready ? 'dn__pill dn__pill--yellow' : 'dn__pill dn__pill--mute'}
      disabled={!ready}
      onClick={() => ready && onClaim?.(tier.id)}
    >
      {label}
    </button>
  );
}

/**
 * @param {{ onLoadingChange?: (loading: boolean) => void }} props
 */
function FreeRewardsContent({ onLoadingChange }) {
  const [vip, setVip] = useState(null);
  const [referral, setReferral] = useState(null);
  const [copied, setCopied] = useState(false);
  const [redeemCode, setRedeemCode] = useState('');
  const [redeemBusy, setRedeemBusy] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [loading, setLoading] = useState(true);
  const [isGuest, setIsGuest] = useState(() => !isUserSessionActive());

  const promptRegister = useCallback(() => {
    openAuthIfGuest('register');
  }, []);

  const loadRewards = useCallback(async () => {
    setLoading(true);
    const guest = !isUserSessionActive();
    setIsGuest(guest);
    if (guest) {
      setLoadError('');
      setLoading(false);
      return;
    }
    setLoadError('');
    try {
      const [v, r] = await Promise.all([rewards.getVip(), rewards.getReferral()]);
      setVip(v);
      setReferral(r);
    } catch (err) {
      setLoadError(err?.message || 'Could not load rewards.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRewards();
  }, [loadRewards]);

  useEffect(() => {
    onLoadingChange?.(loading);
  }, [loading, onLoadingChange]);

  useEffect(() => {
    const onAuth = () => {
      if (isUserSessionActive()) loadRewards();
    };
    window.addEventListener('czutka-auth', onAuth);
    return () => window.removeEventListener('czutka-auth', onAuth);
  }, [loadRewards]);

  const refShareUrl = safeReferralUrl(referral?.code);
  const refDisplay = refShareUrl ? refShareUrl.replace(/^https:\/\//, '') : '';

  const afterBalanceChange = async (res) => {
    if (res?.balance != null) {
      await refreshBalance({ PLN: res.balance });
    } else {
      await refreshBalance();
    }
  };

  const copyRef = async () => {
    if (!refShareUrl) return;
    try {
      await navigator.clipboard.writeText(refShareUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const claimBonus = async (kind) => {
    if (openLoginIfGuest()) return;
    try {
      const res = await rewards.claimBonus(kind);
      await afterBalanceChange(res);
      const v = await rewards.getVip();
      setVip(v);
      toastChipCredit('Bonus claimed —', res.amount);
    } catch (err) {
      toastError(err?.message || 'Could not claim bonus.');
    }
  };

  const claimReferral = async (tier) => {
    if (openLoginIfGuest()) return;
    try {
      const res = await rewards.claimReferralTier(tier);
      await afterBalanceChange(res);
      const r = await rewards.getReferral();
      setReferral(r);
      toastChipCredit('Reward claimed —', res.amount);
    } catch (err) {
      toastError(err?.message || 'Could not claim reward.');
    }
  };

  const submitRedeem = async (e) => {
    e.preventDefault();
    if (isGuest) {
      promptRegister();
      return;
    }
    const code = redeemCode.trim();
    if (!code || redeemBusy) return;
    if (openLoginIfGuest()) return;
    setRedeemBusy(true);
    try {
      const res = await rewards.redeemCode(code);
      await afterBalanceChange(res);
      setRedeemCode('');
      toastChipCredit('Code activated —', res.amount);
    } catch (err) {
      toastError(err?.message || 'Invalid or already used code.');
    } finally {
      setRedeemBusy(false);
    }
  };

  const pct = vip?.progress?.pct ?? 0;
  const referralTiers =
    referral?.tiers?.length > 0 ? referral.tiers : DEFAULT_REFERRAL_TIERS;

  return (
    <div className="dn__content">
      {loadError ? <p className="dn__load-error" role="alert">{loadError}</p> : null}
      <div className="dn__row dn__row--rewards">
        <div className="dn__stack">
          <section>
            <h2 className="dn__section-label">Free rewards</h2>
            {isGuest ? (
              <p className="dn__guest-hint">
                Create an account to track VIP progress, claim bonuses, and unlock your referral link.
              </p>
            ) : null}
            <div className="dn__surface dn__surface--vip">
              <div className="dn__vip-progress-stack">
                <div className="dn__vip-head">
                  <span>{isGuest ? 'VIP progress' : 'Your VIP progress'}</span>
                  <span className="dn__vip-percent">{pct.toFixed(2)}%</span>
                </div>
                <div
                  className="dn__progress-shell"
                  role="progressbar"
                  aria-valuenow={Math.round(pct)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="VIP progress"
                >
                  <div className="dn__progress-fill" style={{ width: `${Math.min(100, pct)}%` }} />
                </div>
                <div className="dn__tier-labels">
                  <span>{vip?.progress?.fromTier ?? 'Bronze'}</span>
                  <span>{vip?.progress?.toTier ?? 'Silver'}</span>
                </div>
              </div>
              <div>
                <p className="dn__subsection-title dn__subsection-title--spaced">VIP rewards</p>
                <div className="dn__vip-grid-wrap">
                  <div className="dn__vip-row">
                    <div className="dn__vip-cell">
                      <span className="dn__cell-title">Daily bonus</span>
                      <BonusPill
                        bonus={vip?.bonuses?.daily}
                        kind="daily"
                        onClaim={claimBonus}
                        guest={isGuest}
                        onRegister={promptRegister}
                      />
                    </div>
                    <div className="dn__vip-cell">
                      <span className="dn__cell-title">Weekly bonus</span>
                      <BonusPill
                        bonus={vip?.bonuses?.weekly}
                        kind="weekly"
                        onClaim={claimBonus}
                        guest={isGuest}
                        onRegister={promptRegister}
                      />
                    </div>
                  </div>
                  <div className="dn__vip-row">
                    <div className="dn__vip-cell">
                      <span className="dn__cell-title">Monthly bonus</span>
                      <BonusPill
                        bonus={vip?.bonuses?.monthly}
                        kind="monthly"
                        onClaim={claimBonus}
                        guest={isGuest}
                        onRegister={promptRegister}
                      />
                    </div>
                    <div className="dn__vip-cell">
                      <span className="dn__cell-title">Rank bonus</span>
                      <BonusPill
                        bonus={vip?.bonuses?.rank}
                        kind="rank"
                        onClaim={claimBonus}
                        guest={isGuest}
                        onRegister={promptRegister}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <div className="dn__stack dn__stack--right">
          <section>
            <h3 className="dn__heading-split">{isGuest ? 'Free rewards tasks' : 'Claim free rewards'}</h3>
            <div className="dn__surface dn__surface--tasks">
              <div className="dn__task-block">
                <span className="dn__field-label" id="dn-discord-label">
                  Discord
                </span>
                <div className="dn__compound" aria-labelledby="dn-discord-label">
                  <input
                    type="text"
                    readOnly
                    className="dn__compound-text dn__compound-text--readonly"
                    value={DISCORD_LABEL}
                    tabIndex={-1}
                    aria-hidden
                  />
                  <a className="dn__compound-btn" href={DISCORD_URL} target="_blank" rel="noopener noreferrer">
                    Join
                  </a>
                </div>
              </div>
              <div className="dn__task-block">
                <span className="dn__field-label" id="dn-telegram-label">
                  Telegram
                </span>
                <div className="dn__compound" aria-labelledby="dn-telegram-label">
                  <input
                    type="text"
                    readOnly
                    className="dn__compound-text dn__compound-text--readonly"
                    value={TELEGRAM_LABEL}
                    tabIndex={-1}
                    aria-hidden
                  />
                  <a className="dn__compound-btn" href={TELEGRAM_URL} target="_blank" rel="noopener noreferrer">
                    Join
                  </a>
                </div>
              </div>
              <form className="dn__task-block dn__task-block--redeem" onSubmit={submitRedeem}>
                <span className="dn__field-label" id="dn-redeem-label">
                  Reward code
                </span>
                <p className="dn__redeem-hint">
                  {isGuest
                    ? 'Register to redeem reward codes from Discord.'
                    : 'Add czutkabet.com to your Discord nickname, get a code via DM, and enter it below.'}
                </p>
                <div className="dn__compound" aria-labelledby="dn-redeem-label">
                  <input
                    type="text"
                    className="dn__compound-text"
                    value={redeemCode}
                    onChange={(e) => setRedeemCode(e.target.value)}
                    placeholder={isGuest ? 'Available after registration' : 'Enter code'}
                    autoComplete="off"
                    spellCheck={false}
                    disabled={isGuest}
                    readOnly={isGuest}
                  />
                  <button
                    type="submit"
                    className="dn__compound-btn"
                    disabled={!isGuest && (!redeemCode.trim() || redeemBusy)}
                  >
                    {isGuest ? 'Register' : redeemBusy ? '…' : 'Claim'}
                  </button>
                </div>
              </form>
            </div>
          </section>
        </div>
      </div>

      <section className="dn__polecenia-row" aria-labelledby="dn-polecenia-heading">
        <h2 id="dn-polecenia-heading" className="dn__section-label dn__section-label--polecenia">
          Referrals
        </h2>
        <div className="dn__polecenia-grid">
          <div className="dn__polecenia-col dn__polecenia-col--rewards">
            <h3 className="dn__polecenia-subtitle">Claim rewards</h3>
            <div className="dn__surface dn__surface--vip">
              <div className="dn__vip-grid-wrap">
                {Array.from({ length: Math.ceil(referralTiers.length / 2) }).map((_, rowIdx) => {
                  const pair = referralTiers.slice(rowIdx * 2, rowIdx * 2 + 2);
                  return (
                    <div key={rowIdx} className="dn__vip-row">
                      {pair.map((tier) => (
                        <div key={tier.id} className="dn__vip-cell">
                          <span className="dn__cell-title">{tier.label}</span>
                          <CurrencyAmount
                            className="dn__ref-amount"
                            value={tier.amount}
                            decimals={0}
                            size={20}
                          />
                          <ReferralPill
                            tier={tier}
                            onClaim={claimReferral}
                            guest={isGuest}
                            onRegister={promptRegister}
                          />
                        </div>
                      ))}
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
          <div className="dn__polecenia-col dn__polecenia-col--link">
            <h3 className="dn__polecenia-subtitle">{isGuest ? 'Your referral link' : 'Your link'}</h3>
            <div className="dn__surface dn__surface--tasks">
              <div className="dn__task-block">
                <div className="dn__task-line">
                  <span className="dn__step-index">1</span>
                  <span className="dn__task-title">
                    {isGuest ? 'Get your referral link' : 'Copy your referral link'}
                  </span>
                </div>
                <div className="dn__compound">
                  <span className="dn__compound-text">
                    {isGuest ? 'Available after registration' : refDisplay || '—'}
                  </span>
                  <button
                    type="button"
                    className="dn__compound-btn"
                    onClick={isGuest ? promptRegister : copyRef}
                    disabled={!isGuest && !refShareUrl}
                  >
                    {isGuest ? 'Register' : copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>
              <p className="dn__referral-explainer">
                {isGuest
                  ? 'Register to get your personal referral link. Share it with friends — for each new account through your link, we credit your balance and unlock tier rewards in Claim rewards.'
                  : 'Share your link with friends — for each new account registered through it, we credit your balance. Reward tier progress grows as more people join via your link; claim tier bonuses in the Claim rewards section. The more referrals you bring, the higher you climb in the program and the better your withdrawal terms.'}
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

export default FreeRewardsContent;
