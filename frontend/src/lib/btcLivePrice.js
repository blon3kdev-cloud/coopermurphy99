/**
 * Shared BTC/USD price feed — GET /api/bitcoin on a clock-aligned schedule so
 * the last fetch in each window lands just before the round ends.
 */

import { apiUrl } from './api/config'
import {
  earliestWindowEndMs,
  nextPollDelayMs,
  remainingSecForWindow,
} from './cryptoWindowClock'

const POLL_INTERVAL_MS = 2_000
const FINAL_POLL_LEAD_MS = 200
const MAX_HISTORY = 400

/** Stable 2-decimal USD — stops 77,223.67 / 77,223.68 flicker from float noise. */
export function roundBtcUsd(price) {
  return Math.round(Number(price) * 100) / 100
}

/** @type {Set<(price: number) => void>} */
const listeners = new Set()
/** @type {Set<(windows: Record<string, unknown>) => void>} */
const windowListeners = new Set()
/** @type {number | null} */
let currentPrice = null
/** @type {Record<string, unknown> | null} */
let currentWindows = null
/** @type {Record<string, unknown> | null} */
let currentFairOdds = null
/** @type {Set<(meta: Record<string, unknown>) => void>} */
const fairOddsListeners = new Set()
/** @type {{ time: number; value: number }[]} */
const priceHistory = []

/** @type {ReturnType<typeof setInterval> | null} */
let pollTimer = null
/** @type {Promise<void> | null} */
let snapshotInflight = null
/** @type {(() => void) | null} */
let visibilityCleanup = null

function parsePrice(msg) {
  if (!msg || typeof msg !== 'object') return null
  const p = typeof msg.price === 'number' ? msg.price : Number(msg.price)
  return Number.isFinite(p) && p > 0 ? p : null
}

function applySnapshot(msg) {
  if (!msg || typeof msg !== 'object') return
  const price = parsePrice(msg)
  if (price != null) emit(price)
  if (msg.windows && typeof msg.windows === 'object') {
    currentWindows = msg.windows
    windowListeners.forEach((fn) => fn(msg.windows))
  }
  if (msg.fairOdds && typeof msg.fairOdds === 'object') {
    currentFairOdds = msg.fairOdds
    fairOddsListeners.forEach((fn) => fn(msg.fairOdds))
  }
}

function emit(price) {
  const rounded = roundBtcUsd(price)
  if (rounded === currentPrice) return
  currentPrice = rounded
  priceHistory.push({ time: Date.now() / 1000, value: rounded })
  if (priceHistory.length > MAX_HISTORY) priceHistory.shift()
  listeners.forEach((fn) => fn(rounded))
}

function stopPollTimer() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
}

function scheduleNextPoll() {
  stopPollTimer()
  const active =
    listeners.size > 0 || windowListeners.size > 0 || fairOddsListeners.size > 0
  if (!active) return
  const delay = nextPollDelayMs(
    earliestWindowEndMs(currentWindows),
    POLL_INTERVAL_MS,
    FINAL_POLL_LEAD_MS,
  )
  pollTimer = setTimeout(() => {
    pollTimer = null
    refreshBtcSnapshot().finally(() => {
      if (
        listeners.size > 0 ||
        windowListeners.size > 0 ||
        fairOddsListeners.size > 0
      ) {
        scheduleNextPoll()
      }
    })
  }, delay)
}

function startPollTimer() {
  stopPollTimer()
  refreshBtcSnapshot().finally(scheduleNextPoll)
}

function onVisibilityChange() {
  const active =
    listeners.size > 0 || windowListeners.size > 0 || fairOddsListeners.size > 0
  if (!active) return
  if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
    stopPollTimer()
  } else {
    startPollTimer()
  }
}

function syncPollTimer() {
  const active =
    listeners.size > 0 || windowListeners.size > 0 || fairOddsListeners.size > 0
  if (active && !pollTimer) {
    if (!visibilityCleanup && typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', onVisibilityChange)
      visibilityCleanup = () => {
        document.removeEventListener('visibilitychange', onVisibilityChange)
        visibilityCleanup = null
      }
    }
    if (typeof document === 'undefined' || document.visibilityState !== 'hidden') {
      startPollTimer()
    }
  } else if (!active) {
    stopPollTimer()
    visibilityCleanup?.()
  }
}

/** Single in-flight fetch shared by all charts. */
export async function refreshBtcSnapshot() {
  if (snapshotInflight) return snapshotInflight
  snapshotInflight = (async () => {
    try {
      const res = await fetch(apiUrl('/bitcoin'), { cache: 'no-store' })
      if (!res.ok) return
      applySnapshot(await res.json())
    } catch {
      /* ignore */
    } finally {
      snapshotInflight = null
    }
  })()
  return snapshotInflight
}

export function getBtcHistory() {
  return priceHistory.slice()
}

export function getBtcPrice() {
  return currentPrice
}

export function getBtcFairOddsMeta() {
  return currentFairOdds
}

/**
 * @param {(meta: Record<string, unknown>) => void} fn
 * @returns {() => void}
 */
export function subscribeBtcFairOdds(fn) {
  fairOddsListeners.add(fn)
  if (currentFairOdds) fn(currentFairOdds)
  syncPollTimer()
  return () => {
    fairOddsListeners.delete(fn)
    syncPollTimer()
  }
}

/**
 * @param {(price: number) => void} fn
 * @returns {() => void}
 */
export function subscribeBtcPrice(fn) {
  listeners.add(fn)
  if (currentPrice != null) fn(currentPrice)
  syncPollTimer()
  return () => {
    listeners.delete(fn)
    syncPollTimer()
  }
}

/**
 * @param {(windows: Record<string, unknown>) => void} fn
 * @returns {() => void}
 */
export function subscribeBtcWindows(fn) {
  windowListeners.add(fn)
  if (currentWindows) fn(currentWindows)
  syncPollTimer()
  return () => {
    windowListeners.delete(fn)
    syncPollTimer()
  }
}

/** Remaining seconds until window end from server snapshot. */
export function remainingSecFromWindow(w, windowKey) {
  if (w?.windowEnd != null && windowKey) {
    return remainingSecForWindow(windowKey, w.windowEnd)
  }
  if (w?.windowEnd != null) {
    return Math.max(0, Math.ceil((w.windowEnd - Date.now()) / 1000))
  }
  return Math.max(0, Math.floor(w?.remainingSec ?? 0))
}
