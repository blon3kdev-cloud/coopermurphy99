import { useEffect, useRef, useState } from 'react'
import { getBtcPrice, roundBtcUsd } from './btcLivePrice.js'

const btcPriceFmt = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

function fmtBtcPrice(v) {
  return btcPriceFmt.format(roundBtcUsd(v)) + '\u00a0$'
}

function easeOutCubic(t) {
  return 1 - (1 - t) ** 3
}

const TICK_MS = 420

const ARROW_UP_PATH =
  'M9.52231 14.25C8.27409 14.25 7.57194 12.8144 8.33828 11.8291L10.816 8.64354C11.4165 7.87143 12.5835 7.87142 13.184 8.64354L15.6617 11.8291C16.428 12.8144 15.7259 14.25 14.4777 14.25H9.52231Z'

function PriceDirectionArrow({ direction }) {
  if (!direction) return null
  return (
    <span
      className={`bety-krypto__price-dir bety-krypto__price-dir--${direction}`}
      aria-hidden="true"
    >
      <svg
        className="bety-krypto__price-dir-ico"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 24 24"
        fill="none"
      >
        <path d={ARROW_UP_PATH} fill="currentColor" />
      </svg>
    </span>
  )
}

/**
 * Counts price up/down with a brief scale pulse; shows green/red arrow for direction.
 * @param {{ price: number | null | undefined }} props
 */
export function AnimatedCryptoPrice({ price }) {
  const [display, setDisplay] = useState(() => {
    const p = price ?? getBtcPrice()
    return p != null ? roundBtcUsd(p) : null
  })
  const [direction, setDirection] = useState(null)
  const [pulsing, setPulse] = useState(false)
  const displayRef = useRef(display)
  const rafRef = useRef(null)
  const pulseTimerRef = useRef(null)

  useEffect(() => {
    displayRef.current = display
  }, [display])

  useEffect(() => {
    if (price == null) {
      const cached = getBtcPrice()
      if (cached != null) {
        const rounded = roundBtcUsd(cached)
        if (displayRef.current !== rounded) setDisplay(rounded)
      } else {
        setDisplay(null)
        setDirection(null)
      }
      return undefined
    }

    const target = roundBtcUsd(price)
    const from =
      displayRef.current != null ? displayRef.current : target

    if (from === target) {
      if (displayRef.current !== target) setDisplay(target)
      return undefined
    }

    const nextDir = target > from ? 'up' : 'down'
    setDirection(nextDir)

    const reduced =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduced) {
      setDisplay(target)
      setPulse(true)
      pulseTimerRef.current = window.setTimeout(() => setPulse(false), 180)
      return () => {
        if (pulseTimerRef.current) clearTimeout(pulseTimerRef.current)
      }
    }

    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    setPulse(true)

    const start = performance.now()

    const step = (now) => {
      const t = Math.min(1, (now - start) / TICK_MS)
      const eased = easeOutCubic(t)
      const value = from + (target - from) * eased
      setDisplay(value)

      if (t < 1) {
        rafRef.current = requestAnimationFrame(step)
      } else {
        setDisplay(target)
        rafRef.current = null
        pulseTimerRef.current = window.setTimeout(() => setPulse(false), 120)
      }
    }

    rafRef.current = requestAnimationFrame(step)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (pulseTimerRef.current) clearTimeout(pulseTimerRef.current)
    }
  }, [price])

  useEffect(
    () => () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (pulseTimerRef.current) clearTimeout(pulseTimerRef.current)
    },
    [],
  )

  if (display == null) {
    return <span className="bety-krypto__price-value">—</span>
  }

  return (
    <div className="bety-krypto__current-row">
      <span
        className={`bety-krypto__price-value${pulsing ? ' bety-krypto__price-value--tick' : ''}`}
      >
        {fmtBtcPrice(display)}
      </span>
      <PriceDirectionArrow direction={direction} />
    </div>
  )
}
