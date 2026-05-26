const SHARE_HOST =
  (process.env.REACT_APP_REFERRAL_HOST || 'czutkabet.com').replace(/^https?:\/\//, '').split('/')[0];

/**
 * @param {{ id?: string; title?: string }} bet
 * @param {{ winAmount?: string }} [opts]
 */
export function buildBetShareUrl(bet, opts = {}) {
  const origin =
    typeof window !== 'undefined' && window.location?.origin
      ? window.location.origin
      : `https://${SHARE_HOST}`;
  const params = new URLSearchParams();
  if (bet?.id) params.set('bet', String(bet.id));
  if (opts.winAmount) params.set('win', String(opts.winAmount));
  const qs = params.toString();
  return `${origin}/your-bets${qs ? `?${qs}` : ''}`;
}

/**
 * @param {{ title?: string; answer?: string; winAmount?: string }} bet
 */
export function buildBetShareText(bet, winAmount) {
  const parts = ['Wygrałem na czutkabet.com!'];
  if (bet?.title) parts.push(bet.title);
  if (bet?.answer) parts.push(`→ ${bet.answer}`);
  if (winAmount) parts.push(`Wygrana: ${winAmount}`);
  return parts.join(' · ');
}

/** @param {'x' | 'facebook' | 'telegram' | 'whatsapp'} platform */
export function openBetShare(platform, url, text) {
  const encodedUrl = encodeURIComponent(url);
  const encodedText = encodeURIComponent(text);
  let href = url;
  if (platform === 'x') {
    href = `https://twitter.com/intent/tweet?url=${encodedUrl}&text=${encodedText}`;
  } else if (platform === 'facebook') {
    href = `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`;
  } else if (platform === 'telegram') {
    href = `https://t.me/share/url?url=${encodedUrl}&text=${encodedText}`;
  } else if (platform === 'whatsapp') {
    href = `https://wa.me/?text=${encodeURIComponent(`${text}\n${url}`)}`;
  }
  window.open(href, '_blank', 'noopener,noreferrer');
}

export { downloadBetShareCard } from '../components/share-bet-sheet/ShareBetDownloadCard';
