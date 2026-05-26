import React from 'react';
import { createRoot } from 'react-dom/client';
import html2canvas from 'html2canvas';
import { BrandLogo } from '../brand/BrandLogo';
import { BetTicketCluster } from '../bet-ticket/BetTicket';
import '../bet-ticket/BetTicket.css';
import './ShareBetDownloadCard.css';

const BRAND_HOST = (process.env.REACT_APP_REFERRAL_HOST || 'czutkabet.com')
  .replace(/^https?:\/\//, '')
  .split('/')[0];

const STAT_LABELS = {
  multiplier: 'mnożnik',
  cost: 'koszt',
  win: 'potencjalna wygrana',
};

function resolveSlipBets(bet, bets) {
  if (Array.isArray(bets) && bets.length) return bets;
  if (bet) return [bet];
  return [];
}

/**
 * @param {{ bet?: object; bets?: object[]; totalWin?: string }} props
 */
export function ShareBetDownloadCard({ bet, bets, totalWin }) {
  const slipBets = resolveSlipBets(bet, bets);
  if (!slipBets.length) return null;

  const isParlay = slipBets.length > 1;
  const lastIdx = slipBets.length - 1;
  const mappedBets = slipBets.map((leg, index) =>
    index === lastIdx ? { ...leg, potWin: totalWin ?? leg.potWin } : leg,
  );

  return (
    <div className="share-dl" data-share-export>
      <header className="share-dl__brand">
        <BrandLogo size={30} color="#000000" className="share-dl__brand-mark" />
        <span className="share-dl__brand-name">{BRAND_HOST}</span>
      </header>
      <div className="share-dl__ticket">
        <BetTicketCluster
          bets={mappedBets}
          isParlay={isParlay}
          showFullStats
          showCostChip={false}
          statLabels={STAT_LABELS}
        />
      </div>
    </div>
  );
}

/** html2canvas cannot clip gradient to text — draw glyphs to canvas, swap in <img>. */
function createGradientWinImage(text, styles) {
  const trimmed = String(text || '').trim();
  if (!trimmed) return null;

  const fontSize = parseFloat(styles?.fontSize) || 28;
  const fontWeight = styles?.fontWeight || '700';
  const font = `${fontWeight} ${fontSize}px Inter, system-ui, sans-serif`;
  const dpr = 2;

  const measure = document.createElement('canvas').getContext('2d');
  if (!measure) return null;
  measure.font = font;
  const width = Math.ceil(measure.measureText(trimmed).width + 4);
  const height = Math.ceil(fontSize * 1.15);

  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  canvas.width = width * dpr;
  canvas.height = height * dpr;
  ctx.scale(dpr, dpr);
  ctx.font = font;
  ctx.textBaseline = 'alphabetic';

  const gradient = ctx.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0.15364, '#ff9d00');
  gradient.addColorStop(0.81848, '#ffd600');
  ctx.fillStyle = gradient;
  ctx.fillText(trimmed, 0, fontSize * 0.92);

  const img = document.createElement('img');
  img.src = canvas.toDataURL('image/png');
  img.alt = '';
  img.width = width;
  img.height = height;
  img.style.cssText = `width:${width}px;height:${height}px;display:block;flex-shrink:0;`;
  img.setAttribute('data-share-win', '1');
  return img;
}

function replaceWinAmountsWithGradientImages(root) {
  const wins = [...root.querySelectorAll('.yb__stat-win')];
  return wins.map((el) => {
    const styles = getComputedStyle(el);
    const img = createGradientWinImage(el.textContent, styles);
    if (!img) {
      el.style.background = 'none';
      el.style.webkitTextFillColor = '#ffd600';
      el.style.color = '#ffd600';
      return null;
    }
    el.replaceWith(img);
    return img;
  }).filter(Boolean);
}

function waitForImages(root) {
  const imgs = [...root.querySelectorAll('img')];
  return Promise.all(
    imgs.map(
      (img) =>
        new Promise((resolve) => {
          if (img.complete) {
            resolve();
            return;
          }
          img.addEventListener('load', resolve, { once: true });
          img.addEventListener('error', resolve, { once: true });
        }),
    ),
  );
}

/**
 * @param {{ bet?: object; bets?: object[]; totalWin?: string }} opts
 */
export async function downloadBetShareCard({ bet, bets, totalWin }) {
  const host = document.createElement('div');
  host.setAttribute('aria-hidden', 'true');
  host.style.cssText =
    'position:fixed;left:-10000px;top:0;z-index:-1;pointer-events:none;';
  document.body.appendChild(host);

  const root = createRoot(host);
  root.render(<ShareBetDownloadCard bet={bet} bets={bets} totalWin={totalWin} />);

  try {
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const card = host.querySelector('[data-share-export]');
    if (!card) return;

    await document.fonts?.ready;
    replaceWinAmountsWithGradientImages(card);
    await waitForImages(card);

    const canvas = await html2canvas(card, {
      scale: 2,
      useCORS: true,
      backgroundColor: '#ffd600',
      logging: false,
    });

    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
    if (!blob) return;

    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'czutka-bet.png';
    a.click();
    URL.revokeObjectURL(url);
  } finally {
    root.unmount();
    host.remove();
  }
}

export default ShareBetDownloadCard;
