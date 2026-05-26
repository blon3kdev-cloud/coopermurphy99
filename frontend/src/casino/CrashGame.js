import { haptic } from '../lib/haptics.js'
import { sanitizeHtml } from '../lib/sanitizeHtml.js'
import { crashBet, crashCashout, crashCancelBet, fetchCrashState } from '../lib/api/casino.js'
import { wsUrl } from '../lib/api/config.js'
import { refreshBalance, getWalletCurrencyId } from '../lib/walletCurrency.js'
import { ApiError } from '../lib/api/client.js'
import { openLoginIfGuest } from '../lib/betsApi.js'
import sndWin from '../assets/audio/games/winlimbo.mp3'
import sndLose from '../assets/audio/games/lose.mp3'
import {
  createCrashChart,
  elapsedFromMult,
  multFromElapsed,
} from './crashChart.js'

const HISTORY_MAX = 12
const WIN_THRESHOLD = 2.0
const CASHOUT_UNSET = 'Not set'
/** Must match backend `crash_engine.GROWTH_RATE` */
const GROWTH_RATE = 0.0693

function fmtMult(n) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '×'
}

function fmtPln(n) {
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function parseTargetRaw(str) {
  return Number.parseFloat(String(str).replace(/\s/g, '').replace(',', '.'))
}

function isCashoutUnset(str) {
  const t = String(str ?? '').trim()
  return !t || /^not\s*set$/i.test(t)
}


function normalizeMyBet(raw) {
  if (!raw) return null
  return {
    stake: raw.stake,
    autoCashout: raw.autoCashout ?? raw.auto_cashout ?? null,
    cashedOut: Boolean(raw.cashedOut ?? raw.cashed_out),
    cashoutAt: raw.cashoutAt ?? raw.cashout_at ?? null,
    payout: raw.payout ?? 0,
  }
}

function normalizeQueuedBet(raw) {
  if (!raw) return null
  return {
    stake: raw.stake,
    autoCashout: raw.autoCashout ?? raw.auto_cashout ?? null,
  }
}

function hasOwn(snap, key) {
  return Object.prototype.hasOwnProperty.call(snap, key)
}

export function mountCrashGame({ gameHost, shell }) {
  let phase = 'waiting'
  let multiplier = 1
  let serverMultiplier = 1
  let displayMultiplier = 1
  let countdown = 0
  let roundId = 0
  let myBet = null
  let queuedBet = null
  let history = []
  let ws = null
  let wsReconnectTimer = 0
  let destroyed = false
  let rafId = 0
  const activeSounds = new Set()
  let runStartMs = 0
  let frozenElapsedSec = 0
  let frozenHeadMult = 1
  /** True after manual cashout modal — skip duplicate win UI when the round crashes. */
  let cashoutModalShown = false

  const chart = createCrashChart(GROWTH_RATE)

  function playSound(src, vol = 0.6) {
    if (destroyed) return
    try {
      const a = new Audio(src)
      a.volume = vol
      activeSounds.add(a)
      const release = () => activeSounds.delete(a)
      a.addEventListener('ended', release, { once: true })
      a.play().catch(release)
    } catch (_) {}
  }

  function stopAllSounds() {
    for (const a of activeSounds) {
      try {
        a.pause()
        a.currentTime = 0
      } catch (_) {}
    }
    activeSounds.clear()
  }

  const root = document.createElement('div')
  root.className = 'crash'
  root.innerHTML = `
    <div class="crash__history" data-crash-history aria-live="polite"></div>
    <div class="crash__stage">
      <canvas class="crash__canvas" data-crash-canvas aria-hidden="true"></canvas>
      <div class="crash__overlay">
        <div class="crash__mult" data-crash-mult>1.00×</div>
        <div class="crash__status" data-crash-status hidden></div>
      </div>
    </div>
  `

  const historyEl = root.querySelector('[data-crash-history]')
  const multEl = root.querySelector('[data-crash-mult]')
  const statusEl = root.querySelector('[data-crash-status]')
  const canvas = root.querySelector('[data-crash-canvas]')
  const ctx = canvas.getContext('2d')
  const cashoutInp = shell.el?.querySelector('[data-crash-sidebar-cashout]')
  const btnBet = shell.el?.querySelector('[data-crypto-postaw]')
  const btnCashout = shell.el?.querySelector('[data-crypto-wyplac]')

  function syncCashoutFieldStyle() {
    if (!cashoutInp) return
    cashoutInp.classList.toggle('casino-stat-field__input--unset', isCashoutUnset(cashoutInp.value))
  }

  function getAutoCashout() {
    if (!cashoutInp || isCashoutUnset(cashoutInp.value)) return null
    const v = parseTargetRaw(cashoutInp.value)
    if (!Number.isFinite(v) || v < 1.01) return null
    return v
  }

  function applyUserBets(snap) {
    if (hasOwn(snap, 'myBet')) myBet = normalizeMyBet(snap.myBet)
    if (hasOwn(snap, 'queuedBet')) queuedBet = normalizeQueuedBet(snap.queuedBet)
    if (myBet && queuedBet) queuedBet = null
  }

  function getLiveBet() {
    if (myBet && !myBet.cashedOut) return myBet
    return null
  }

  function projectedPayout() {
    const bet = getLiveBet()
    if (!bet?.stake) return 0
    const mult = phase === 'running' ? displayMultiplier : serverMultiplier
    return Math.round(bet.stake * mult * 100) / 100
  }

  function renderHistory() {
    historyEl.innerHTML = sanitizeHtml(
      history
        .slice(-HISTORY_MAX)
        .reverse()
        .map((value) => {
          const win = value >= WIN_THRESHOLD
          return `<span class="crash__pill crash__pill--${win ? 'win' : 'lose'}">${fmtMult(value)}</span>`
        })
        .join(''),
    )
  }

  function resizeCanvas() {
    const rect = canvas.parentElement.getBoundingClientRect()
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.max(1, Math.floor(rect.width * dpr))
    canvas.height = Math.max(1, Math.floor(rect.height * dpr))
    canvas.style.width = `${rect.width}px`
    canvas.style.height = `${rect.height}px`
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  }

  function syncRunClock(serverElapsedSec) {
    if (!Number.isFinite(serverElapsedSec) || serverElapsedSec < 0) return
    const idealStart = performance.now() - serverElapsedSec * 1000
    if (!runStartMs) {
      runStartMs = idealStart
      return
    }
    const driftMs = idealStart - runStartMs
    if (Math.abs(driftMs) > 40) runStartMs += driftMs * 0.25
  }

  function getElapsedSec() {
    if (phase === 'crashed') return frozenElapsedSec
    if (phase !== 'running' || !runStartMs) return 0
    return Math.max(0, (performance.now() - runStartMs) / 1000)
  }

  function getHeadMult(elapsedSec) {
    return multFromElapsed(elapsedSec, GROWTH_RATE)
  }

  function tickDisplayMultiplier() {
    if (phase === 'running' && runStartMs) {
      const curve = getHeadMult(getElapsedSec())
      displayMultiplier += (curve - displayMultiplier) * 0.22
      displayMultiplier += (serverMultiplier - displayMultiplier) * 0.08
      multiplier = displayMultiplier
      return
    }
    if (phase === 'crashed') {
      displayMultiplier += (multiplier - displayMultiplier) * 0.25
      return
    }
    displayMultiplier = 1
    multiplier = 1
  }

  function drawGraph() {
    const w = canvas.clientWidth
    const h = canvas.clientHeight
    ctx.clearRect(0, 0, w, h)
    if (phase !== 'running' && phase !== 'crashed') return

    const elapsedSec = getElapsedSec()
    const headMult =
      phase === 'crashed' ? frozenHeadMult : getHeadMult(elapsedSec)
    if (elapsedSec <= 0 && headMult <= 1) return

    chart.draw(ctx, w, h, {
      elapsedSec,
      headMult,
      crashed: phase === 'crashed',
    })
  }

  function setMultDisplay() {
    const shown = phase === 'running' ? displayMultiplier : multiplier
    multEl.textContent = fmtMult(shown)
    multEl.dataset.state = phase === 'crashed' ? 'crashed' : phase === 'running' ? 'running' : 'idle'
  }

  function updateStatus() {
    if (phase === 'waiting' && countdown > 0) {
      statusEl.hidden = false
      statusEl.textContent = `Starting in ${countdown.toFixed(2)}s`
      statusEl.dataset.tone = 'wait'
    } else {
      statusEl.hidden = true
    }
  }

  function syncButtons() {
    const liveBet = getLiveBet()
    const hasQueued = Boolean(queuedBet)
    const canCashout = phase === 'running' && Boolean(liveBet)
    const waitingForNextRound = hasQueued && phase !== 'waiting'
    const canCancel =
      !canCashout &&
      phase === 'waiting' &&
      (Boolean(liveBet) || hasQueued)

    if (btnCashout) btnCashout.hidden = true

    if (!btnBet) return

    btnBet.hidden = false
    btnBet.classList.remove(
      'crypto-casino__btn--crash-cancel',
      'crypto-casino__btn--crash-cashout',
    )

    if (canCashout) {
      btnBet.dataset.crashMode = 'cashout'
      btnBet.disabled = false
      btnBet.classList.add('crypto-casino__btn--crash-cashout')
      btnBet.textContent = `Cashout · ${fmtPln(projectedPayout())}`
    } else if (canCancel) {
      btnBet.dataset.crashMode = 'cancel'
      btnBet.disabled = false
      btnBet.classList.add('crypto-casino__btn--crash-cancel')
      btnBet.textContent = 'Anuluj'
    } else if (waitingForNextRound) {
      btnBet.dataset.crashMode = 'waiting'
      btnBet.disabled = true
      btnBet.textContent = 'Waiting for next round'
    } else {
      btnBet.dataset.crashMode = 'bet'
      btnBet.disabled = false
      if (!liveBet && !hasQueued) {
        btnBet.textContent = phase === 'running' ? 'Bet next round' : 'Bet'
      } else {
        btnBet.textContent = 'Place bet'
      }
    }
  }

  function applySnapshot(snap) {
    if (destroyed) return
    const prevPhase = phase
    const prevRoundId = roundId
    phase = snap.phase ?? phase
    serverMultiplier = snap.multiplier ?? serverMultiplier
    countdown = snap.countdown ?? countdown
    roundId = snap.roundId ?? roundId
    history = snap.history ?? history
    applyUserBets(snap)

    if (roundId !== prevRoundId && prevRoundId !== 0) {
      cashoutModalShown = false
    }

    if (snap.balance != null) refreshBalance({ PLN: snap.balance })

    if (phase === 'running') {
      if (prevPhase !== 'running' || roundId !== prevRoundId) {
        runStartMs = 0
        displayMultiplier = 1
        chart.reset()
      }
      const elapsed =
        typeof snap.elapsed === 'number'
          ? snap.elapsed
          : elapsedFromMult(serverMultiplier, GROWTH_RATE)
      syncRunClock(elapsed)
    } else if (phase === 'waiting') {
      runStartMs = 0
      frozenElapsedSec = 0
      frozenHeadMult = 1
      displayMultiplier = 1
      serverMultiplier = 1
      multiplier = 1
      chart.reset()
    } else if (phase === 'crashed') {
      multiplier = serverMultiplier
      displayMultiplier = serverMultiplier
      frozenHeadMult = serverMultiplier
      frozenElapsedSec = elapsedFromMult(serverMultiplier, GROWTH_RATE)
      runStartMs = 0
    }

    if (phase === 'crashed' && prevPhase === 'running') {
      const settled = myBet
      const won = settled?.cashedOut
      if (won && settled.payout > 0 && !cashoutModalShown) {
        haptic('medium')
        playSound(sndWin, 0.7)
        shell.showResultModal(
          true,
          settled.cashoutAt ?? multiplier,
          settled.payout - settled.stake,
        )
      } else if (!won) {
        haptic('medium')
        playSound(sndLose, 0.7)
      }
      cashoutModalShown = false
    }

    tickDisplayMultiplier()
    setMultDisplay()
    updateStatus()
    renderHistory()
    syncButtons()
  }

  function connectWs() {
    window.clearTimeout(wsReconnectTimer)
    wsReconnectTimer = 0
    ws = new WebSocket(wsUrl('/games/crash/ws'))
    ws.onopen = () => {
      refreshState()
    }
    ws.onmessage = (ev) => {
      if (destroyed) return
      try {
        applySnapshot(JSON.parse(ev.data))
      } catch (_) {}
    }
    ws.onclose = () => {
      if (!destroyed) {
        wsReconnectTimer = window.setTimeout(connectWs, 1500)
      }
    }
  }

  function onVisibilityChange() {
    if (!destroyed && document.visibilityState === 'visible') refreshState()
  }

  async function refreshState() {
    try {
      applySnapshot(await fetchCrashState())
    } catch (_) {}
  }

  async function placeBet() {
    if (openLoginIfGuest()) return
    const bet = shell.getBetAmount()
    if (bet < 0.01) {
      haptic('warning')
      return
    }
    shell.dismissResultModal?.()
    shell.setLoading?.(true)
    try {
      const data = await crashBet({
        betAmount: bet,
        autoCashout: getAutoCashout(),
        currency: getWalletCurrencyId(),
      })
      applySnapshot(data)
      shell.clearGameError?.()
      haptic('medium')
    } catch (err) {
      shell.showGameError?.(err instanceof ApiError ? err.message : 'Could not place bet')
      haptic('warning')
    } finally {
      shell.setLoading?.(false)
    }
  }

  async function cashOut() {
    shell.setLoading?.(true)
    try {
      const data = await crashCashout()
      applySnapshot(data)
      if (data.payout > 0) {
        haptic('success')
        cashoutModalShown = true
        shell.showResultModal(true, data.cashoutAt ?? multiplier, data.payout - (myBet?.stake ?? 0))
      }
    } catch (err) {
      shell.showGameError?.(err instanceof ApiError ? err.message : 'Cash out failed')
      haptic('warning')
    } finally {
      shell.setLoading?.(false)
    }
  }

  async function cancelBet() {
    shell.setLoading?.(true)
    try {
      const data = await crashCancelBet()
      applySnapshot(data)
      shell.clearGameError?.()
      haptic('light')
    } catch (err) {
      shell.showGameError?.(err instanceof ApiError ? err.message : 'Could not cancel bet')
      haptic('warning')
    } finally {
      shell.setLoading?.(false)
    }
  }

  async function primaryAction() {
    const mode = btnBet?.dataset.crashMode ?? 'bet'
    if (mode === 'cancel') return cancelBet()
    if (mode === 'cashout') return cashOut()
    return placeBet()
  }

  if (cashoutInp) {
    cashoutInp.addEventListener('focus', () => {
      if (isCashoutUnset(cashoutInp.value)) {
        cashoutInp.value = ''
        syncCashoutFieldStyle()
      }
    })
    cashoutInp.addEventListener('blur', () => {
      if (!cashoutInp.value.trim()) {
        cashoutInp.value = CASHOUT_UNSET
      }
      syncCashoutFieldStyle()
    })
    cashoutInp.addEventListener('input', syncCashoutFieldStyle)
    syncCashoutFieldStyle()
  }

  function onResize() {
    resizeCanvas()
    drawGraph()
  }

  const stageEl = root.querySelector('.crash__stage')
  const resizeObs =
    typeof ResizeObserver !== 'undefined' ? new ResizeObserver(onResize) : null
  resizeObs?.observe(stageEl)

  gameHost.innerHTML = ''
  gameHost.appendChild(root)
  resizeCanvas()
  chart.reset()
  window.addEventListener('resize', onResize)
  document.addEventListener('visibilitychange', onVisibilityChange)
  connectWs()
  refreshState()

  function loop() {
    if (!destroyed) {
      tickDisplayMultiplier()
      setMultDisplay()
      drawGraph()
      if (myBet || queuedBet || phase === 'waiting' || phase === 'running') syncButtons()
    }
    rafId = requestAnimationFrame(loop)
  }
  rafId = requestAnimationFrame(loop)

  return {
    playRound: primaryAction,
    destroy() {
      destroyed = true
      window.clearTimeout(wsReconnectTimer)
      wsReconnectTimer = 0
      stopAllSounds()
      cancelAnimationFrame(rafId)
      resizeObs?.disconnect()
      window.removeEventListener('resize', onResize)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      if (ws) {
        ws.onmessage = null
        ws.onclose = null
        ws.close()
        ws = null
      }
    },
  }
}
