import { useEffect, useMemo, useRef, useState } from 'react'
import { pickCryptoOdds } from '../lib/cryptoOdds'
import {
  getBtcPrice,
  refreshBtcSnapshot,
  roundBtcUsd,
  subscribeBtcFairOdds,
  subscribeBtcPrice,
  subscribeBtcWindows,
} from '../lib/btcLivePrice'
import { remainingSecForWindow, windowRolledOver } from '../lib/cryptoWindowClock'

/**
 * Live Higher/Lower odds for a BTC window — recalculated on every price tick and each second.
 * @param {string | null | undefined} windowKey e.g. "5m", "30m"
 */
export function useLiveCryptoOdds(windowKey) {
  const [price, setPrice] = useState(() => getBtcPrice())
  const [win, setWin] = useState(null)
  const [fairOdds, setFairOdds] = useState(null)
  const [remaining, setRemaining] = useState(0)

  useEffect(
    () =>
      subscribeBtcPrice((p) => {
        setPrice((prev) => {
          const next = roundBtcUsd(p)
          return next === prev ? prev : next
        })
      }),
    [],
  )

  useEffect(() => {
    if (!windowKey) return undefined
    return subscribeBtcWindows((windows) => {
      const w = windows?.[windowKey]
      if (w) setWin(w)
    })
  }, [windowKey])

  useEffect(() => subscribeBtcFairOdds(setFairOdds), [])

  useEffect(() => {
    const tick = () => {
      if (win?.windowEnd != null && windowKey) {
        setRemaining(remainingSecForWindow(windowKey, win.windowEnd))
      } else {
        setRemaining(Math.max(0, Math.floor(win?.remainingSec ?? 0)))
      }
    }
    tick()
    const timer = setInterval(tick, 1_000)
    return () => clearInterval(timer)
  }, [win, windowKey])

  const lastRolledSig = useRef(null)
  useEffect(() => {
    if (!windowKey || win?.windowEnd == null || !windowRolledOver(windowKey, win.windowEnd)) {
      lastRolledSig.current = null
      return
    }
    const sig = `${windowKey}:${win.windowEnd}`
    if (lastRolledSig.current === sig) return
    lastRolledSig.current = sig
    refreshBtcSnapshot()
  }, [windowKey, win?.windowEnd])

  const odds = useMemo(() => {
    const open = win?.openPrice
    if (!windowKey) return { up: null, down: null }
    const meta = { ...(fairOdds || {}), ...(win?.oddsContext || {}) }
    const picked = pickCryptoOdds(windowKey, win?.odds, meta, price, open, remaining)
    return { up: picked.up, down: picked.down }
  }, [windowKey, price, win?.openPrice, win?.odds, win?.oddsContext, fairOdds, remaining])

  return { ...odds, price, remaining, openPrice: win?.openPrice ?? null }
}
