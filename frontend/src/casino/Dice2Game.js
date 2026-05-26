import { haptic } from '../lib/haptics.js'
import { startDice2, rollDice2, cashoutDice2 } from '../lib/api/casino.js'
import { refreshBalance } from '../lib/walletCurrency.js'
import { ApiError } from '../lib/api/client.js'
import sndTick from '../assets/audio/games/dice2/tick.DZo2-5dJ.mp3'
import sndBet from '../assets/audio/games/dice2/bet.DUx2OBl3.mp3'
import sndRoll from '../assets/audio/games/dice2/rollDice.BLvcu4Xk.mp3'
import sndWin from '../assets/audio/games/dice2/win.BN9s2WFF.mp3'
import sndLose from '../assets/audio/games/dice2/lose.CSJf_1E1.mp3'

const GRID = 4
const PATH = [
  [0, 0], [0, 1], [0, 2], [0, 3],
  [1, 3], [2, 3], [3, 3],
  [3, 2], [3, 1], [3, 0],
  [2, 0], [1, 0],
]
const CENTER = new Set(['1,1', '1,2', '2,1', '2,2'])
const STEP_MS = 140
const DICE_ROLL_MS = 420
const PATH_LEN = PATH.length
const GOLDEN_INDEX = 6

/** Hardcoded boards (must match backend/app/dice2_engine.py). */
const DICE2_BOARDS = {
  easy: {
    goldenMult: 1.95,
    deadly: new Set([5, 7]),
    mults: {
      1: 1.52, 2: 1.07, 3: 1.05, 4: 1.05, 8: 1.05, 9: 1.05, 10: 1.14, 11: 1.07,
    },
  },
  medium: {
    goldenMult: 2.25,
    deadly: new Set([2, 5, 7]),
    mults: {
      1: 1.61, 3: 1.08, 4: 1.05, 8: 1.05, 9: 1.05, 10: 1.21, 11: 1.13,
    },
  },
  hard: {
    goldenMult: 2.55,
    deadly: new Set([5, 7, 9]),
    mults: {
      1: 1.64, 2: 1.16, 3: 1.1, 4: 1.05, 8: 1.05, 10: 1.23, 11: 1.16,
    },
  },
}

function normalizeDifficulty(raw) {
  if (raw === 'easy' || raw === 'hard') return raw
  return 'medium'
}

function buildPreviewTiles(difficulty = 'medium') {
  const preset = DICE2_BOARDS[normalizeDifficulty(difficulty)]
  const tiles = []
  for (let i = 0; i < PATH_LEN; i++) {
    if (i === 0) {
      tiles.push({ start: true })
    } else if (preset.deadly.has(i)) {
      tiles.push({ deadly: true })
    } else if (i === GOLDEN_INDEX) {
      tiles.push({ golden: true, mult: preset.goldenMult })
    } else {
      tiles.push({ mult: preset.mults[i] ?? 0.78 })
    }
  }
  return tiles
}

const ICON_PLAY = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M11.1967 2.71828C8.53683 0.970354 5 2.8783 5 6.0611V17.9387C5 21.1215 8.53684 23.0294 11.1967 21.2815L20.234 15.3427C22.6384 13.7627 22.6384 10.2371 20.234 8.65706L11.1967 2.71828Z" fill="currentColor"/></svg>`
const ICON_DEADLY = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M10.6056 3.56142C9.36475 2.98888 8.05693 2.86598 6.83124 3.13927C4.90318 3.56917 3.26845 4.96089 2.48959 6.90295C0.885443 10.9029 2.98361 16.5927 11.5115 21.3725C11.8153 21.5428 12.1857 21.5428 12.4894 21.3725C21.0173 16.5927 23.1154 10.9028 21.5112 6.90294C20.7324 4.96087 19.0977 3.56916 17.1696 3.13926C15.8029 2.83454 14.3342 3.02239 12.9699 3.77687C11.8874 4.94224 11.1058 6.64664 11.0099 8.59567L14.1441 11.7299L12.9487 15.3162C12.774 15.8401 12.2077 16.1233 11.6838 15.9486C11.1598 15.774 10.8767 15.2077 11.0513 14.6837L11.8559 12.2701L9 9.41418V8.99996C9 6.98104 9.60494 5.08074 10.6056 3.56142Z" fill="currentColor"/></svg>`

function fmtMult(n) {
  return `${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}x`
}

function fmtWin(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '0.00'
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function pathIndexFor(r, c) {
  return PATH.findIndex(([pr, pc]) => pr === r && pc === c)
}

function posKey(r, c) {
  return `${r},${c}`
}

function wait(ms) {
  return new Promise((resolve) => { window.setTimeout(resolve, ms) })
}

function playSound(src, vol = 0.55) {
  try {
    const a = new Audio(src)
    a.volume = vol
    a.play().catch(() => {})
  } catch (_) {}
}

function rollDieAnim() {
  return 1 + Math.floor(Math.random() * 6)
}

function pipHtml(n) {
  const on = {
    1: [4],
    2: [0, 8],
    3: [0, 4, 8],
    4: [0, 2, 6, 8],
    5: [0, 2, 4, 6, 8],
    6: [0, 1, 2, 6, 7, 8],
  }[n] || []
  return Array.from({ length: 9 }, (_, i) =>
    `<span class="dice2__pip${on.includes(i) ? ' dice2__pip--on' : ''}"></span>`,
  ).join('')
}

export function mountDice2Game({ gameHost, shell }) {
  let phase = 'idle'
  let pathPos = 0
  let combinedMult = 1
  /** @type {Array<{ start?: boolean; deadly?: boolean; golden?: boolean; mult?: number }>} */
  let tileMeta = []
  let busy = false
  let dieA = 1
  let dieB = 1
  let startShowsMult = false
  let hasRolled = false
  let multCountRaf = 0
  let lastPayout = 0
  let projectedServerPayout = 0

  const btnBet = shell.el?.querySelector('[data-crypto-postaw]')
  const btnRoll = shell.el?.querySelector('[data-dice2-roll]')

  const root = document.createElement('div')
  root.className = 'dice2'
  root.innerHTML = `
    <div class="dice2__board" data-dice2-board aria-label="Dice2 board"></div>
  `

  const boardEl = root.querySelector('[data-dice2-board]')
  const tileEls = new Map()
  let hubDieA
  let hubDieB
  let hubMultVal

  function applyBalances(balances) {
    if (balances != null) refreshBalance(balances)
  }

  function buildBoard() {
    boardEl.innerHTML = ''
    tileEls.clear()

    for (let r = 0; r < GRID; r++) {
      for (let c = 0; c < GRID; c++) {
        const key = posKey(r, c)
        if (CENTER.has(key)) continue

        const idx = pathIndexFor(r, c)
        const el = document.createElement('button')
        el.type = 'button'
        el.className = 'dice2__tile'
        el.style.gridRow = String(r + 1)
        el.style.gridColumn = String(c + 1)
        el.dataset.pathIdx = String(idx)
        el.disabled = true
        el.setAttribute('aria-label', `Tile ${idx + 1}`)
        boardEl.appendChild(el)
        tileEls.set(idx, el)
      }
    }

    const hub = document.createElement('div')
    hub.className = 'dice2__hub'
    hub.style.gridRow = '2 / span 2'
    hub.style.gridColumn = '2 / span 2'
    hub.innerHTML = `
      <div class="dice2__dice-row">
        <div class="dice2__die" data-dice2-die-a aria-label="Die 1"></div>
        <div class="dice2__die" data-dice2-die-b aria-label="Die 2"></div>
      </div>
      <div class="dice2__total" data-dice2-total>
        <span class="dice2__total-val" data-dice2-total-val>1.00x</span>
      </div>
    `
    boardEl.appendChild(hub)
    hubDieA = hub.querySelector('[data-dice2-die-a]')
    hubDieB = hub.querySelector('[data-dice2-die-b]')
    hubMultVal = hub.querySelector('[data-dice2-total-val]')
  }

  function renderDie(el, value) {
    if (!el) return
    el.innerHTML = `<span class="dice2__pip-grid">${pipHtml(value)}</span>`
    el.dataset.value = String(value)
  }

  function syncHub() {
    renderDie(hubDieA, dieA)
    renderDie(hubDieB, dieB)
    if (multCountRaf) return
    if (hubMultVal) hubMultVal.textContent = fmtMult(combinedMult)
    hubMultVal?.classList.remove('dice2__total-val--counting')
    hubMultVal?.style.removeProperty('transform')
  }

  function stopMultCount() {
    if (multCountRaf) {
      cancelAnimationFrame(multCountRaf)
      multCountRaf = 0
    }
    hubMultVal?.classList.remove('dice2__total-val--counting')
    hubMultVal?.style.removeProperty('transform')
  }

  function animateMultCount(from, to) {
    if (!hubMultVal || from === to) {
      combinedMult = to
      return Promise.resolve()
    }

    stopMultCount()
    playSound(sndTick, 0.48)
    hubMultVal.classList.add('dice2__total-val--counting')

    const duration = 520
    return new Promise((resolve) => {
      const start = performance.now()

      function frame() {
        const elapsed = performance.now() - start
        const t = Math.min(elapsed / duration, 1)
        const eased = 1 - (1 - t) ** 3
        const val = from + (to - from) * eased
        hubMultVal.textContent = fmtMult(val)
        const scale = 1 + 0.18 * Math.sin(Math.min(t, 1) * Math.PI)
        hubMultVal.style.transform = `scale(${scale.toFixed(3)})`

        if (t < 1) {
          multCountRaf = requestAnimationFrame(frame)
        } else {
          multCountRaf = 0
          combinedMult = to
          hubMultVal.textContent = fmtMult(to)
          hubMultVal.classList.remove('dice2__total-val--counting')
          hubMultVal.style.transform = 'scale(1.06)'
          syncSidebar()
          resolve()
        }
      }

      multCountRaf = requestAnimationFrame(frame)
    })
  }

  function projectedPayout() {
    if (lastPayout > 0) return lastPayout
    if (projectedServerPayout > 0) return projectedServerPayout
    const bet = shell.getBetAmount()
    return Math.round(bet * combinedMult * 100) / 100
  }

  function renderTiles() {
    tileEls.forEach((el, idx) => {
      const meta = tileMeta[idx]
      el.className = 'dice2__tile'
      el.innerHTML = ''
      if (idx === 0) {
        if (startShowsMult) {
          el.textContent = fmtMult(1)
          el.setAttribute('aria-label', 'Multiplier 1.00x')
        } else {
          el.classList.add('dice2__tile--start')
          el.innerHTML = `<span class="dice2__tile-icon dice2__tile-icon--play">${ICON_PLAY}</span>`
          el.setAttribute('aria-label', 'Start')
        }
        return
      }
      if (meta?.deadly) {
        el.classList.add('dice2__tile--deadly')
        el.innerHTML = `<span class="dice2__tile-icon dice2__tile-icon--deadly">${ICON_DEADLY}</span>`
        el.setAttribute('aria-label', 'Deadly tile')
        return
      }
      if (meta?.golden) {
        el.classList.add('dice2__tile--golden')
        el.innerHTML = `
          <span class="dice2__tile-shine" aria-hidden="true"></span>
          <span class="dice2__tile-label">${fmtMult(meta.mult ?? 1)}</span>`
        el.setAttribute('aria-label', `Golden multiplier ${fmtMult(meta.mult ?? 1)}`)
        return
      }
      el.textContent = fmtMult(meta?.mult ?? 1)
      el.setAttribute('aria-label', `Multiplier ${fmtMult(meta?.mult ?? 1)}`)
    })
  }

  function clearLandedStyles() {
    tileEls.forEach((el) => {
      el.classList.remove('dice2__tile--safe', 'dice2__tile--bust')
    })
  }

  function loadTilesFromServer(tiles) {
    tileMeta = Array.isArray(tiles) ? tiles : []
    pathPos = 0
    combinedMult = 1
    dieA = 1
    dieB = 1
    startShowsMult = false
    hasRolled = false
    lastPayout = 0
    projectedServerPayout = 0
    syncHub()
    renderTiles()
    clearLandedStyles()
  }

  function revealStartMultiplier() {
    if (startShowsMult) return
    startShowsMult = true
    const startEl = tileEls.get(0)
    if (!startEl) return
    startEl.classList.remove('dice2__tile--start')
    startEl.innerHTML = ''
    startEl.textContent = fmtMult(1)
    startEl.setAttribute('aria-label', 'Multiplier 1.00x')
  }

  function currentDifficulty() {
    return normalizeDifficulty(shell.getDice2Difficulty?.() ?? 'medium')
  }

  function refreshPreviewBoard() {
    if (phase !== 'idle') return
    loadTilesFromServer(buildPreviewTiles(currentDifficulty()))
  }

  function syncSidebar() {
    const inRound = phase === 'playing'
    const betInput = shell.el?.querySelector('[data-crypto-bet]')
    shell.setDice2DifficultyDisabled?.(inRound || busy)
    if (btnBet) {
      if (inRound) {
        btnBet.textContent = `Cashout · ${fmtWin(projectedPayout())}`
        btnBet.classList.add('crypto-casino__btn--cashout')
        btnBet.disabled = busy || !hasRolled
      } else {
        btnBet.textContent = 'Bet'
        btnBet.classList.remove('crypto-casino__btn--cashout')
        btnBet.disabled = busy
      }
    }
    if (btnRoll) btnRoll.disabled = !inRound || busy
    if (betInput) betInput.disabled = inRound || busy
  }

  function endRound() {
    phase = 'idle'
    busy = false
    lastPayout = 0
    projectedServerPayout = 0
    loadTilesFromServer(buildPreviewTiles(currentDifficulty()))
    syncSidebar()
    shell.setLoading(false)
  }

  function onDifficultyChange() {
    haptic('selection')
    refreshPreviewBoard()
  }

  const difficultySelect = shell.el?.querySelector('[data-dice2-difficulty]')
  difficultySelect?.addEventListener('change', onDifficultyChange)

  function showCashout(payout) {
    const bet = shell.getBetAmount()
    const paid = Number(payout) || projectedPayout()
    const profit = paid - bet
    if (profit > 0.005) {
      playSound(sndWin, 0.65)
      shell.showResultModal?.(true, combinedMult, profit)
    } else {
      playSound(sndLose, 0.5)
      shell.showResultModal?.(false, combinedMult, 0, {
        lossAmount: Math.max(0, bet - paid),
      })
    }
    endRound()
  }

  function showLoss() {
    playSound(sndLose, 0.65)
    shell.showResultModal?.(false, combinedMult, 0)
    endRound()
  }

  async function animateHop(fromIdx, hopCount) {
    if (hopCount <= 0) return fromIdx

    let cur = fromIdx

    for (let s = 0; s < hopCount; s++) {
      const next = (cur + 1) % PATH.length
      const fromEl = tileEls.get(cur)
      const toEl = tileEls.get(next)

      fromEl?.classList.add('dice2__tile--leave')
      await wait(STEP_MS * 0.45)
      fromEl?.classList.remove('dice2__tile--leave', 'dice2__tile--safe')

      cur = next
      toEl?.classList.add('dice2__tile--hop')
      await wait(STEP_MS * 0.55)
      toEl?.classList.remove('dice2__tile--hop')
    }
    return cur
  }

  async function animateDiceRoll(nextA, nextB) {
    playSound(sndRoll, 0.5)
    root.classList.add('dice2--rolling')
    hubDieA?.classList.add('dice2__die--roll')
    hubDieB?.classList.add('dice2__die--roll')

    const tick = window.setInterval(() => {
      renderDie(hubDieA, rollDieAnim())
      renderDie(hubDieB, rollDieAnim())
    }, 70)

    await wait(DICE_ROLL_MS)
    window.clearInterval(tick)
    dieA = nextA
    dieB = nextB
    renderDie(hubDieA, dieA)
    renderDie(hubDieB, dieB)
    hubDieA?.classList.remove('dice2__die--roll')
    hubDieB?.classList.remove('dice2__die--roll')
    root.classList.remove('dice2--rolling')
  }

  async function startRound() {
    if (busy || phase === 'playing') return
    const bet = shell.getBetAmount()
    if (bet < 0.01) {
      haptic('warning')
      return
    }

    shell.clearGameError?.()
    shell.dismissResultModal?.()
    busy = true
    syncSidebar()
    shell.setLoading(true)

    let data
    try {
      data = await startDice2({ betAmount: bet, difficulty: currentDifficulty() })
    } catch (err) {
      busy = false
      shell.setLoading(false)
      syncSidebar()
      haptic('warning')
      shell.showGameError?.(
        err instanceof ApiError ? err.message : 'Could not place bet',
      )
      return
    }

    applyBalances(data.balances)
    if (data.difficulty && difficultySelect) {
      difficultySelect.value = normalizeDifficulty(data.difficulty)
    }
    loadTilesFromServer(data.tiles)
    pathPos = data.pathPos ?? 0
    combinedMult = data.combinedMult ?? 1
    hasRolled = Boolean(data.hasRolled)
    projectedServerPayout = Number(data.projectedPayout) || 0
    syncHub()

    haptic('medium')
    playSound(sndBet, 0.5)
    phase = 'playing'
    busy = false
    shell.setLoading(false)
    syncSidebar()
  }

  async function roll() {
    if (phase !== 'playing' || busy) return
    busy = true
    syncSidebar()
    shell.setLoading(true)
    haptic('light')

    let data
    try {
      data = await rollDice2()
    } catch (err) {
      busy = false
      shell.setLoading(false)
      syncSidebar()
      haptic('warning')
      shell.showGameError?.(
        err instanceof ApiError ? err.message : 'Could not roll',
      )
      return
    }

    const prevMult = combinedMult
    const nextA = data.dieA
    const nextB = data.dieB
    const steps = nextA + nextB
    const nextMult = data.combinedMult ?? combinedMult

    await animateDiceRoll(nextA, nextB)
    clearLandedStyles()

    const fromPos = pathPos
    pathPos = await animateHop(fromPos, steps)
    pathPos = data.pathPos ?? pathPos
    hasRolled = true
    revealStartMultiplier()

    const landed = tileEls.get(pathPos)
    const meta = tileMeta[pathPos]

    if (data.busted || meta?.deadly) {
      combinedMult = nextMult
      landed?.classList.add('dice2__tile--bust')
      applyBalances(data.balances)
      haptic('error')
      await wait(320)
      showLoss()
      return
    }

    landed?.classList.add('dice2__tile--safe')
    haptic('success')

    if (nextMult !== prevMult) {
      await animateMultCount(prevMult, nextMult)
    } else {
      combinedMult = nextMult
      syncHub()
    }

    projectedServerPayout = Number(data.projectedPayout) || projectedServerPayout

    busy = false
    shell.setLoading(false)
    syncSidebar()
  }

  async function cashout() {
    if (phase !== 'playing' || busy || !hasRolled) return
    busy = true
    syncSidebar()
    shell.setLoading(true)
    haptic('success')

    let data
    try {
      data = await cashoutDice2()
    } catch (err) {
      busy = false
      shell.setLoading(false)
      syncSidebar()
      haptic('warning')
      shell.showGameError?.(
        err instanceof ApiError ? err.message : 'Could not cash out',
      )
      return
    }

    applyBalances(data.balances)
    lastPayout = Number(data.payout) || 0
    combinedMult = data.combinedMult ?? combinedMult
    showCashout(lastPayout)
  }

  function onPrimary() {
    if (phase === 'playing') cashout()
    else startRound()
  }

  function onRollClick(e) {
    e.preventDefault()
    roll()
  }

  btnRoll?.addEventListener('click', onRollClick)

  buildBoard()
  loadTilesFromServer(buildPreviewTiles(currentDifficulty()))
  phase = 'idle'
  syncSidebar()
  gameHost.appendChild(root)

  return {
    playRound: onPrimary,
    destroy() {
      stopMultCount()
      btnRoll?.removeEventListener('click', onRollClick)
      difficultySelect?.removeEventListener('change', onDifficultyChange)
      root.remove()
    },
  }
}
