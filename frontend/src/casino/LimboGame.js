import { haptic } from '../lib/haptics.js'
import { sanitizeHtml } from '../lib/sanitizeHtml.js'
import { playLimbo } from '../lib/api/casino.js'
import { refreshBalance, getWalletCurrencyId } from '../lib/walletCurrency.js'
import { ApiError } from '../lib/api/client.js'
import sndTick from '../assets/audio/games/ticklimbo.mp3'
import sndWin from '../assets/audio/games/winlimbo.mp3'
import sndLose from '../assets/audio/games/lose.mp3'

const HISTORY_MAX = 8
const LIMBO_TARGET_MIN = 1.01

function rollResult() {
  const r = Math.random()
  return Math.max(1.00, +(99 / Math.max(r * 100, 1)).toFixed(2))
}

function fmtMult(n) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '×'
}

function fmtTarget(n) {
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function parseTargetRaw(str) {
  return Number.parseFloat(String(str).replace(/\s/g, '').replace(',', '.'))
}

function playSound(src, vol = 0.6) {
  try { const a = new Audio(src); a.volume = vol; a.play().catch(() => {}) } catch (_) {}
}

export function mountLimboGame({ gameHost, shell }) {
  const history = []
  let idle = true

  const root = document.createElement('div')
  root.className = 'limbo'
  root.innerHTML = `
    <div class="limbo__history" aria-live="polite" aria-label="Result history"></div>
    <div class="limbo__stage">
      <div class="limbo__mult" data-limbo-mult>1,00×</div>
    </div>
    <div class="limbo__controls">
      <div class="casino-stat-field">
        <label class="casino-stat-field__label" for="limbo-chance-inp">Win chance</label>
        <div class="casino-stat-field__box">
          <input type="text" id="limbo-chance-inp"
            class="casino-stat-field__input casino-stat-field__input--readonly"
            data-limbo-chance value="49,50" readonly tabindex="-1" />
          <span class="casino-stat-field__suffix">%</span>
        </div>
      </div>
    </div>
  `

  const multEl    = root.querySelector('[data-limbo-mult]')
  const historyEl = root.querySelector('.limbo__history')
  const targetInp = shell.el?.querySelector('[data-limbo-sidebar-target]')
  const chanceInp = root.querySelector('[data-limbo-chance]')

  function getTarget() {
    if (!targetInp) return 2
    const v = parseTargetRaw(targetInp.value)
    if (!Number.isFinite(v)) return 2
    return Math.max(LIMBO_TARGET_MIN, v)
  }

  function commitTargetField() {
    if (!targetInp) return
    const v = parseTargetRaw(targetInp.value)
    let n = Number.isFinite(v) ? v : 2
    if (n < LIMBO_TARGET_MIN) n = LIMBO_TARGET_MIN
    targetInp.value = fmtTarget(n)
    syncChance()
  }

  function syncChance() {
    if (!chanceInp) return
    chanceInp.value = Math.min(99, 99 / getTarget()).toFixed(2).replace('.', ',')
  }
  if (targetInp) {
    targetInp.addEventListener('input', syncChance)
    targetInp.addEventListener('blur', commitTargetField)
    targetInp.addEventListener('change', commitTargetField)
  }

  function setMult(value, state = 'idle') {
    multEl.textContent = fmtMult(value)
    multEl.dataset.state = state
  }

  function renderHistory() {
    historyEl.innerHTML = sanitizeHtml(
      history
        .slice(-HISTORY_MAX)
        .reverse()
        .map(({ value, won }) =>
          `<span class="limbo__pill limbo__pill--${won ? 'win' : 'lose'}">${fmtMult(value)}</span>`
        )
        .join('')
    )
  }

  async function playRound() {
    if (!idle) return
    const bet = shell.getBetAmount()
    if (bet < 0.01) { haptic('warning'); return }

    shell.dismissResultModal?.()

    commitTargetField()
    const target = getTarget()
    shell.setLoading?.(true)
    let result
    let newBalances = null
    let data
    try {
      data = await playLimbo({
        target,
        betAmount: bet,
        currency: getWalletCurrencyId(),
      })
    } catch (err) {
      shell.setLoading?.(false)
      idle = true
      if (targetInp) targetInp.disabled = false
      haptic('warning')
      shell.showGameError?.(
        err instanceof ApiError ? err.message : 'Could not place bet',
      )
      return
    }
    const raw = data?.result
    const parsed = typeof raw === 'number' ? raw : Number.parseFloat(String(raw ?? '').replace(',', '.'))
    if (!Number.isFinite(parsed)) {
      shell.setLoading?.(false)
      idle = true
      if (targetInp) targetInp.disabled = false
      haptic('warning')
      return
    }
    result = parsed
    newBalances = data.balances ?? null
    shell.setLoading?.(false)
    shell.clearGameError?.()
    if (newBalances != null) refreshBalance(newBalances)

    const won = result >= target
    const payout = Number(data.payout) || 0

    idle = false
    if (targetInp) targetInp.disabled = true
    haptic('medium')
    setMult(1.00, 'counting')

    const tickAudio = new Audio(sndTick)
    tickAudio.volume = 0.55
    let durationMs = 1100
    tickAudio.playbackRate = 1.35
    tickAudio.addEventListener('loadedmetadata', () => {
      if (tickAudio.duration > 0) {
        durationMs = Math.min(1100, tickAudio.duration * 1000 * 0.5)
      }
    }, { once: true })
    tickAudio.play().catch(() => {})

    const start = performance.now()

    function frame() {
      if (tickAudio.ended) {
        finalize()
        return
      }
      const elapsed = performance.now() - start
      const t = Math.min(elapsed / durationMs, 0.999)
      const eased = 1 - Math.pow(1 - t, 3)
      setMult(+(1 + (result - 1) * eased).toFixed(2), 'counting')
      requestAnimationFrame(frame)
    }

    function finalize() {
      setMult(result, won ? 'win' : 'lose')
      playSound(won ? sndWin : sndLose, 0.72)
      haptic(won ? 'success' : 'medium')
      history.push({ value: result, won })
      renderHistory()
      const profit = won && payout > 0 ? payout - bet : 0
      window.setTimeout(() => {
        shell.showResultModal(won, target, won ? profit : bet)
        window.setTimeout(() => setMult(result, 'idle'), 120)
        idle = true
        if (targetInp) targetInp.disabled = false
      }, 320)
    }

    requestAnimationFrame(frame)
  }

  gameHost.innerHTML = ''
  gameHost.appendChild(root)
  syncChance()

  return { playRound }
}
