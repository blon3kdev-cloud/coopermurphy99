import { haptic } from '../lib/haptics.js'
import { sanitizeHtml } from '../lib/sanitizeHtml.js'
import { playDice } from '../lib/api/casino.js'
import { refreshBalance, getWalletCurrencyId } from '../lib/walletCurrency.js'
import { ApiError } from '../lib/api/client.js'
import sndBet from '../assets/audio/games/dice/bet.mp3'
import sndRolling from '../assets/audio/games/dice/rolling.mp3'
import sndTick from '../assets/audio/games/dice/tick.mp3'
import sndWin from '../assets/audio/games/dice/win.mp3'

const HISTORY_MAX = 8
const MULT_MIN = 1.1
const OVER_MIN = 100 - 99 / MULT_MIN
const OVER_MAX = 98.99

function fmtVal(n, dp = 2) {
  return n.toLocaleString('en-US', { minimumFractionDigits: dp, maximumFractionDigits: dp })
}

function playSound(src, vol = 0.6) {
  try { const a = new Audio(src); a.volume = vol; a.play().catch(() => {}) } catch (_) {}
}

export function mountDiceGame({ gameHost, shell }) {
  const history = []
  let idle = true
  let overValue = 50.50

  const root = document.createElement('div')
  root.className = 'dice'
  root.innerHTML = `
    <div class="dice__history" aria-live="polite" aria-label="Result history"></div>
    <div class="dice__stage">
      <div class="dice__track-area">
        <div class="dice__scale">
          <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
        </div>
        <div class="dice__track-container">
          <div class="dice__bubble" data-dice-bubble></div>
          <div class="dice__track" data-dice-track>
            <div class="dice__fill-lose" data-dice-fill-lose></div>
            <div class="dice__fill-win" data-dice-fill-win></div>
            <div class="dice__handle" data-dice-handle>
              <div class="dice__handle-grip">
                <span class="dice__handle-line"></span>
                <span class="dice__handle-line"></span>
                <span class="dice__handle-line"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="dice__controls">
      <div class="casino-stat-field">
        <label class="casino-stat-field__label" for="dice-mult-inp">Multiplier</label>
        <div class="casino-stat-field__box">
          <input type="text" id="dice-mult-inp" class="casino-stat-field__input" data-dice-mult
            value="2,0000" inputmode="decimal" autocomplete="off" spellcheck="false" />
          <span class="casino-stat-field__suffix">×</span>
        </div>
      </div>
      <div class="casino-stat-field">
        <label class="casino-stat-field__label" for="dice-over-inp">Roll over</label>
        <div class="casino-stat-field__box">
          <input type="text" id="dice-over-inp" class="casino-stat-field__input" data-dice-over
            value="50,50" inputmode="decimal" autocomplete="off" spellcheck="false" />
          <button type="button" class="casino-stat-field__flip" data-dice-flip title="Flip direction" aria-label="Flip">
            <svg viewBox="0 0 20 20" fill="currentColor" width="13" height="13" aria-hidden="true"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg>
          </button>
        </div>
      </div>
      <div class="casino-stat-field">
        <label class="casino-stat-field__label" for="dice-chance-inp">Chance</label>
        <div class="casino-stat-field__box">
          <input type="text" id="dice-chance-inp"
            class="casino-stat-field__input casino-stat-field__input--readonly"
            data-dice-chance value="49,5000" readonly tabindex="-1" />
          <span class="casino-stat-field__suffix">%</span>
        </div>
      </div>
    </div>
  `

  const historyEl = root.querySelector('.dice__history')
  const bubbleEl  = root.querySelector('[data-dice-bubble]')
  const trackEl   = root.querySelector('[data-dice-track]')
  const fillLose  = root.querySelector('[data-dice-fill-lose]')
  const fillWin   = root.querySelector('[data-dice-fill-win]')
  const handle    = root.querySelector('[data-dice-handle]')
  const multInp   = root.querySelector('[data-dice-mult]')
  const overInp   = root.querySelector('[data-dice-over]')
  const chanceInp = root.querySelector('[data-dice-chance]')

  function getMult() {
    return 99 / (100 - overValue)
  }

  function getWinChance() {
    return 100 - overValue
  }

  function syncProfitOnWin() {
    const bet = shell.getBetAmount()
    shell.updateProfit?.(bet * (getMult() - 1))
  }

  function applyOver(val, source = '') {
    overValue = Math.max(OVER_MIN, Math.min(OVER_MAX, val))
    const pct = overValue / 100
    const mult = getMult()
    const chance = getWinChance()

    handle.style.left = `${pct * 100}%`
    fillLose.style.width = `${pct * 100}%`
    fillWin.style.width = `${(1 - pct) * 100}%`

    if (source !== 'over') overInp.value = fmtVal(overValue, 2)
    if (source !== 'mult') multInp.value = fmtVal(mult, 4)
    chanceInp.value = fmtVal(chance, 4)

    syncProfitOnWin()
  }

  function renderHistory() {
    historyEl.innerHTML = sanitizeHtml(
      history
        .slice(-HISTORY_MAX)
        .reverse()
        .map(({ value, won }) =>
          `<span class="dice__pill dice__pill--${won ? 'win' : 'lose'}">${fmtVal(value, 2)}</span>`
        )
        .join('')
    )
  }

  let countRaf = null

  function showBubble(fromPct, toPct, value, won, duration = 500, onDone = null) {
    bubbleEl.className = `dice__bubble dice__bubble--${won ? 'win' : 'lose'}`
    bubbleEl.classList.remove('dice__bubble--bounce')
    bubbleEl.style.left = `${fromPct * 100}%`
    bubbleEl.textContent = fmtVal(0, 2)
    void bubbleEl.offsetHeight
    bubbleEl.classList.add('dice__bubble--visible')

    if (countRaf) cancelAnimationFrame(countRaf)
    const start = performance.now()
    const countDuration = Math.min(260, duration * 0.42)
    function tick() {
      const elapsed = performance.now() - start
      const moveT = Math.min(elapsed / duration, 1)
      const countT = Math.min(elapsed / countDuration, 1)

      const easedMove = 1 - Math.pow(1 - moveT, 3)
      const easedCount = 1 - Math.pow(1 - countT, 3)
      const pos = fromPct + (toPct - fromPct) * easedMove
      bubbleEl.style.left = `${pos * 100}%`
      bubbleEl.textContent = fmtVal(easedCount * value, 2)
      if (moveT < 1) {
        countRaf = requestAnimationFrame(tick)
      } else {
        countRaf = null
        bubbleEl.style.left = `${toPct * 100}%`
        bubbleEl.textContent = fmtVal(value, 2)
        bubbleEl.classList.remove('dice__bubble--bounce')
        void bubbleEl.offsetWidth
        bubbleEl.classList.add('dice__bubble--bounce')
        onDone?.()
      }
    }
    countRaf = requestAnimationFrame(tick)
  }

  function hideBubble() {
    if (countRaf) { cancelAnimationFrame(countRaf); countRaf = null }
    bubbleEl.classList.remove('dice__bubble--bounce')
    bubbleEl.classList.remove('dice__bubble--visible')
  }

  let dragging = false
  let lastTickVal = overValue

  function tickOnMove(newVal) {
    if (Math.abs(newVal - lastTickVal) >= 1) {
      playSound(sndTick, 0.25)
      lastTickVal = newVal
    }
  }

  function pctFromPointer(clientX) {
    const rect = trackEl.getBoundingClientRect()
    return Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
  }

  handle.addEventListener('pointerdown', (e) => {
    if (!idle) return
    dragging = true
    lastTickVal = overValue
    handle.setPointerCapture(e.pointerId)
    haptic('selection')
    e.preventDefault()
  })

  handle.addEventListener('pointermove', (e) => {
    if (!dragging) return
    const newVal = pctFromPointer(e.clientX) * 100
    applyOver(newVal)
    tickOnMove(newVal)
  })

  handle.addEventListener('pointerup', () => { dragging = false })
  handle.addEventListener('pointercancel', () => { dragging = false })

  trackEl.addEventListener('pointerdown', (e) => {
    if (!idle || e.target === handle || handle.contains(e.target)) return
    applyOver(pctFromPointer(e.clientX) * 100)
    haptic('selection')
  })

  overInp.addEventListener('change', () => {
    const v = Number.parseFloat(overInp.value.replace(/\s/g, '').replace(',', '.'))
    if (Number.isFinite(v)) applyOver(v, 'over')
    else overInp.value = fmtVal(overValue, 2)
  })

  multInp.addEventListener('change', () => {
    const m = Number.parseFloat(multInp.value.replace(/\s/g, '').replace(',', '.'))
    if (Number.isFinite(m) && m > 0) {
      const safeMult = Math.max(MULT_MIN, m)
      const newOver = 100 - 99 / safeMult
      applyOver(newOver, 'mult')
    } else {
      multInp.value = fmtVal(getMult(), 4)
    }
  })

  root.addEventListener('click', (e) => {
    if (e.target.closest('[data-dice-flip]')) {
      haptic('light')
      applyOver(100 - overValue)
    }
  })

  async function playRound() {
    if (!idle) return
    const bet = shell.getBetAmount()
    if (bet < 0.01) { haptic('warning'); return }

    shell.dismissResultModal?.()

    shell.setLoading?.(true)
    let result
    let newBalances = null
    let data
    try {
      data = await playDice({
        overValue,
        betAmount: bet,
        currency: getWalletCurrencyId(),
      })
    } catch (err) {
      shell.setLoading?.(false)
      idle = true
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
      haptic('warning')
      return
    }
    result = parsed
    newBalances = data.balances ?? null
    shell.setLoading?.(false)
    shell.clearGameError?.()
    if (newBalances != null) refreshBalance(newBalances)

    idle = false
    hideBubble()
    haptic('medium')
    playSound(sndBet, 0.5)

    const won = result > overValue
    const mult = getMult()
    const payout = Number(data.payout) || 0

    const rollingAudio = new Audio(sndRolling)
    rollingAudio.volume = 0.45
    rollingAudio.play().catch(() => {})

    const duration = 520 + Math.random() * 180
    const resultPct = result / 100
    showBubble(0, resultPct, result, won, duration, settle)

    function settle() {
      rollingAudio.pause()
      rollingAudio.currentTime = 0

      playSound(sndTick, 0.55)

      haptic(won ? 'success' : 'medium')
      if (won) playSound(sndWin, 0.7)

      history.push({ value: result, won })
      renderHistory()

      const profit = won && payout > 0 ? payout - bet : 0
      window.setTimeout(() => {
        shell.showResultModal(won, mult, won ? profit : bet)
        window.setTimeout(() => {
          hideBubble()
          idle = true
        }, 260)
      }, 380)
    }
  }

  shell.onBetChange?.(syncProfitOnWin)

  gameHost.innerHTML = ''
  gameHost.appendChild(root)
  applyOver(overValue)

  return { playRound }
}
