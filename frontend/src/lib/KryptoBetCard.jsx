import { useEffect, useState } from 'react'
import { AnimatedCryptoPrice } from './AnimatedCryptoPrice.jsx'
import { refreshBtcSnapshot, roundBtcUsd, subscribeBtcWindows } from './btcLivePrice.js'
import {
  effectiveWindowEndMs,
  remainingSecForWindow,
  windowRolledOver,
} from './cryptoWindowClock.js'
import { fmtCryptoOddsMult, isCryptoOddsBettable } from './cryptoOdds.js'
import { toastError } from './toast.js'
import { KryptoBtcChart } from '../components/krypto-btc-chart/KryptoBtcChart.jsx'
import { useBetSlip } from '../context/BetSlipContext';
import { useCursorTilt } from '../hooks/useCursorTilt.js'
import { useLiveCryptoOdds } from '../hooks/useLiveCryptoOdds.js'
import btcIcon from '../assets/btc.svg'
import ethIcon from '../assets/eth.svg'
import solIcon from '../assets/sol.svg'
import usdcIcon from '../assets/usdc.svg'

const CRYPTO_ICONS = { btc: btcIcon, eth: ethIcon, sol: solIcon, usdc: usdcIcon }

const RES_UP_PATH =
  'M9.52231 14.25C8.27409 14.25 7.57194 12.8144 8.33828 11.8291L10.816 8.64354C11.4165 7.87143 12.5835 7.87142 13.184 8.64354L15.6617 11.8291C16.428 12.8144 15.7259 14.25 14.4777 14.25H9.52231Z'

function cryptoIconUrl(symbol) {
  return CRYPTO_ICONS[symbol.toLowerCase()] || usdcIcon
}

const btcPriceFmt = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

function fmtBtcPrice(v) {
  return btcPriceFmt.format(roundBtcUsd(v)) + '\u00a0$'
}

function formatSec(sec) {
  const t = Math.max(0, Math.floor(sec))
  const pad = (n) => String(n).padStart(2, '0')
  const h = Math.floor(t / 3600)
  const m = Math.floor((t % 3600) / 60)
  const s = t % 60
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
}

function fmtOpenPrice(openPrice, priceToBeat) {
  if (priceToBeat) return priceToBeat
  if (openPrice != null) return fmtBtcPrice(openPrice)
  return '—'
}

function historyFromWindow(w) {
  const raw = w?.history
  if (Array.isArray(raw) && raw.length > 0) {
    return raw
      .filter((h) => h?.direction === 'up' || h?.direction === 'down')
      .slice(0, 5)
      .map((h) => {
        const openPrice = h.openPrice ?? h.open_price
        return {
          direction: h.direction,
          openPrice,
          priceToBeat: h.priceToBeat ?? (openPrice != null ? fmtBtcPrice(openPrice) : undefined),
        }
      })
  }
  const dirs = w?.resolutions
  if (!Array.isArray(dirs)) return []
  return dirs.filter((d) => d === 'up' || d === 'down').slice(0, 5).map((direction) => ({ direction }))
}

function ResolutionDots({ rounds }) {
  const slots = Array.from({ length: 5 }, (_, i) => rounds[i] ?? null)
  return (
    <div className="bety-krypto__resolutions">
      <div className="bety-krypto__past">
        <span className="bety-krypto__past-label">Past</span>
      </div>
      <span className="bety-krypto__res-vbar" aria-hidden="true" />
      <div className="bety-krypto__res-list" role="list">
        {slots.map((round, i) => {
          if (!round) {
            return (
              <span
                key={i}
                className="bety-krypto__res bety-krypto__res--empty"
                role="listitem"
                aria-hidden="true"
              />
            )
          }
          const label = round.direction === 'up' ? 'Up' : 'Down'
          const ref = fmtOpenPrice(round.openPrice, round.priceToBeat)
          return (
            <span
              key={i}
              className={`bety-krypto__res bety-krypto__res--${round.direction}`}
              role="listitem"
              title={ref !== '—' ? `${label} · reference price ${ref}` : label}
            >
              <svg
                className="bety-krypto__res-ico"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                aria-hidden="true"
              >
                <path d={RES_UP_PATH} fill="currentColor" />
              </svg>
            </span>
          )
        })}
      </div>
    </div>
  )
}

/**
 * @param {{
 *   title: string;
 *   name: string;
 *   symbol: string;
 *   color: string;
 *   window: string;
 *   priceToBeat: string;
 *   windowEnd?: number;
 *   remainingSec: number;
 *   lastResolutions?: ('up'|'down')[];
 *   pastRounds?: { direction: 'up'|'down'; openPrice?: number; priceToBeat?: string }[];
 * }} props
 */
export function KryptoBetCard({
  id,
  title,
  name,
  symbol,
  color,
  window: windowKey,
  priceToBeat: initialPriceToBeat,
  windowEnd: initialWindowEnd,
  remainingSec: initialRemaining,
  lastResolutions,
  pastRounds: initialPastRounds,
}) {
  const tilt = useCursorTilt()
  const { addCryptoBet, bets } = useBetSlip()
  const slipSide = bets.find((b) => b.betId === `crypto-${id}`)?.selectedSide ?? null
  const [priceToBeat, setPriceToBeat] = useState(initialPriceToBeat)
  const liveOdds = useLiveCryptoOdds(windowKey)
  const [windowEnd, setWindowEnd] = useState(initialWindowEnd ?? null)
  const [pastRounds, setPastRounds] = useState(
    () => initialPastRounds?.length
      ? initialPastRounds
      : (lastResolutions ?? []).map((direction) => ({ direction })),
  )
  const [remaining, setRemaining] = useState(() =>
    initialWindowEnd != null
      ? remainingSecForWindow(windowKey, initialWindowEnd)
      : initialRemaining,
  )

  useEffect(() => {
    return subscribeBtcWindows((windows) => {
      const w = windows?.[windowKey]
      if (!w) return
      if (w.openPrice != null) {
        setPriceToBeat(fmtBtcPrice(w.openPrice))
      }
      if (w.windowEnd != null) setWindowEnd(w.windowEnd)
      const hist = historyFromWindow(w)
      if (hist.length > 0) setPastRounds(hist)
    })
  }, [windowKey])

  useEffect(() => {
    const tick = () => {
      if (windowEnd != null) {
        setRemaining(remainingSecForWindow(windowKey, windowEnd))
      } else {
        setRemaining((s) => Math.max(0, s - 1))
      }
    }
    tick()
    const timer = setInterval(tick, 1_000)
    return () => clearInterval(timer)
  }, [windowEnd, windowKey])

  useEffect(() => {
    if (windowEnd == null || !windowRolledOver(windowKey, windowEnd)) return
    const nextEnd = effectiveWindowEndMs(windowKey, windowEnd)
    if (nextEnd != null && nextEnd !== windowEnd) setWindowEnd(nextEnd)
    refreshBtcSnapshot()
  }, [windowKey, windowEnd])

  const slipBet = () => ({
    id,
    title,
    name,
    symbol,
    color,
    priceToBeat,
    remainingSec: remaining,
    lastResolutions: pastRounds.map((r) => r.direction),
  })

  const upBettable = isCryptoOddsBettable(liveOdds.up)
  const downBettable = isCryptoOddsBettable(liveOdds.down)

  const tryAddSide = (side) => {
    const mult = side === 'down' ? liveOdds.down : liveOdds.up
    if (!isCryptoOddsBettable(mult)) {
      toastError('Odds are too low to bet on this side.')
      return
    }
    addCryptoBet(slipBet(), side)
  }

  return (
    <article
      className="featured-krypto__card bety-krypto-card"
      style={{ '--krypto-pfp': color, ...tilt.style }}
      ref={tilt.ref}
      onMouseMove={tilt.onMouseMove}
      onMouseLeave={tilt.onMouseLeave}
      role="button"
      tabIndex={0}
      onClick={() => tryAddSide('up')}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          tryAddSide('up')
        }
      }}
    >
      <div className="bety-card__tilt">
        <div className="bety-krypto__head" aria-label="Header">
          <div className="bety-krypto__pfp-wrap" aria-hidden="true">
            <img
              className="bety-krypto__pfp-img"
              src={cryptoIconUrl(symbol)}
              alt=""
              loading="lazy"
              decoding="async"
            />
          </div>
          <div className="bety-krypto__head-text">
            <h3 className="bety-krypto__title">{title}</h3>
          </div>
          <div className="bety-krypto__head-timer" aria-label="Time until settlement">
            <span className="bety-krypto__price-label">Time left</span>
            <span className="bety-krypto__timer-value">{formatSec(remaining)}</span>
          </div>
        </div>

        <div className="bety-krypto__prices" aria-label="Ceny">
          <div className="bety-krypto__price bety-krypto__price--beat">
            <span className="bety-krypto__price-label">Reference price</span>
            <span className="bety-krypto__price-value">{priceToBeat}</span>
          </div>
          <div className="bety-krypto__price bety-krypto__price--current">
            <span className="bety-krypto__price-label">Current price</span>
            <AnimatedCryptoPrice price={liveOdds.price} />
          </div>
        </div>

        {symbol.toLowerCase() === 'btc' ? <KryptoBtcChart /> : null}

        <ResolutionDots rounds={pastRounds} />

        <div className="bety-krypto__actions" role="group" aria-label="Higher or lower">
          <button
            type="button"
            className={`bety-krypto__odds bety-krypto__odds--yes${slipSide === 'up' ? ' bety-krypto__odds--selected' : ''}${!upBettable ? ' bety-krypto__odds--disabled' : ''}`}
            disabled={!upBettable}
            onClick={(e) => { e.stopPropagation(); tryAddSide('up') }}
          >
            <span className="bety-krypto__odds-label">Higher</span>
            <span className="bety-krypto__odds-mult">{fmtCryptoOddsMult(liveOdds.up)}</span>
          </button>
          <button
            type="button"
            className={`bety-krypto__odds bety-krypto__odds--no${slipSide === 'down' ? ' bety-krypto__odds--selected' : ''}${!downBettable ? ' bety-krypto__odds--disabled' : ''}`}
            disabled={!downBettable}
            onClick={(e) => { e.stopPropagation(); tryAddSide('down') }}
          >
            <span className="bety-krypto__odds-label">Lower</span>
            <span className="bety-krypto__odds-mult">{fmtCryptoOddsMult(liveOdds.down)}</span>
          </button>
        </div>
      </div>
    </article>
  )
}
