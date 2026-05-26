import { useEffect, useState } from 'react'
import {
  getBtcHistory,
  getBtcPrice,
  roundBtcUsd,
  subscribeBtcPrice,
} from '../lib/btcLivePrice'

const CHART_WINDOW_SEC = 30
const MAX_TICKS = 80
const SAMPLE_MS = 500

function trimToWindow(ticks) {
  const cutoff = Date.now() / 1000 - CHART_WINDOW_SEC - 2
  const trimmed = ticks.filter((t) => t.time >= cutoff)
  return trimmed.length > MAX_TICKS ? trimmed.slice(-MAX_TICKS) : trimmed
}

function seedTicks(price) {
  const now = Date.now() / 1000
  const ticks = []
  for (let i = CHART_WINDOW_SEC; i >= 0; i -= 1) {
    ticks.push({ time: now - i, value: price })
  }
  return ticks
}

function baseTicks(ticks, price) {
  const recent = trimToWindow(ticks)
  if (recent.length >= 2) return recent
  return seedTicks(price)
}

function buildChartTicks() {
  const price = getBtcPrice()
  const recent = trimToWindow(getBtcHistory())
  if (recent.length >= 2) return recent
  if (price != null) return seedTicks(roundBtcUsd(price))
  return []
}

function initialValue(ticks) {
  const p = getBtcPrice()
  if (p != null) return roundBtcUsd(p)
  return ticks[ticks.length - 1]?.value ?? 0
}

function appendTick(prev, price, minGapSec = 0) {
  const base = baseTicks(prev, price)
  const t = Date.now() / 1000
  const last = base[base.length - 1]
  if (last && t - last.time < minGapSec) return base
  if (last && last.time === t && last.value === price) return base
  return trimToWindow([...base, { time: t, value: price }])
}

/** Liveline { data, value } from the shared GET /api/bitcoin feed. */
export function useBtcLivelineChart() {
  const [data, setData] = useState(buildChartTicks)
  const [value, setValue] = useState(() => initialValue(buildChartTicks()))
  const [loading, setLoading] = useState(() => buildChartTicks().length < 2)

  useEffect(
    () =>
      subscribeBtcPrice((p) => {
        const rounded = roundBtcUsd(p)
        setValue(rounded)
        setLoading(false)
        setData((prev) => appendTick(prev, rounded))
      }),
    [],
  )

  // Keep the line scrolling between API polls when price is flat.
  useEffect(() => {
    const id = setInterval(() => {
      const p = getBtcPrice()
      if (p == null) return
      const rounded = roundBtcUsd(p)
      setValue(rounded)
      setLoading(false)
      setData((prev) => appendTick(prev, rounded, SAMPLE_MS / 1000))
    }, SAMPLE_MS)
    return () => clearInterval(id)
  }, [])

  return {
    data,
    value,
    windowSec: CHART_WINDOW_SEC,
    loading: loading || data.length < 2,
  }
}
