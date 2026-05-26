/** Fixed windows — must match backend `btc_price._PERIOD_MS`. */
const PERIOD_MS = { '5m': 300_000, '30m': 1_800_000 }

/**
 * When the server window has ended, roll `windowEnd` forward so the UI timer
 * keeps counting toward the current round (5m / 30m only; 24h needs a refresh).
 */
export function effectiveWindowEndMs(windowKey, windowEndMs) {
  if (windowEndMs == null) return null
  const period = PERIOD_MS[windowKey]
  if (!period) return windowEndMs
  let end = windowEndMs
  const now = Date.now()
  while (end <= now) end += period
  return end
}

export function remainingSecForWindow(windowKey, windowEndMs) {
  const end = effectiveWindowEndMs(windowKey, windowEndMs)
  if (end == null) return 0
  return Math.max(0, Math.ceil((end - Date.now()) / 1000))
}

export function windowRolledOver(windowKey, windowEndMs) {
  return windowEndMs != null && windowEndMs <= Date.now()
}

/** Soonest effective window end from a server windows map. */
export function earliestWindowEndMs(windows, keys = ['5m', '30m', '24h']) {
  let min = null
  for (const key of keys) {
    const raw = windows?.[key]?.windowEnd
    if (raw == null) continue
    const end = effectiveWindowEndMs(key, raw)
    if (end != null && (min == null || end < min)) min = end
  }
  return min
}

/**
 * Delay until the next poll. Regular interval between polls; the last poll in
 * each window is scheduled ~leadMs before windowEnd (not after it).
 */
export function nextPollDelayMs(windowEndMs, intervalMs, leadMs = 200) {
  if (windowEndMs == null || intervalMs <= 0) return intervalMs
  const remaining = windowEndMs - Date.now()
  if (remaining <= 0) return intervalMs
  const slots = Math.floor((remaining - leadMs) / intervalMs)
  if (slots <= 0) return Math.max(50, remaining - leadMs)
  return intervalMs
}
