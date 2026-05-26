import { haptic } from '../lib/haptics.js'
import { playKeno } from '../lib/api/casino.js'
import { refreshBalance, optimisticBalanceDelta, getWalletCurrencyId } from '../lib/walletCurrency.js'
import { ApiError } from '../lib/api/client.js'
import gemUrl from '../assets/games/keno/gem.svg'
import sndBet from '../assets/audio/games/bet.mp3'
import sndReveal from '../assets/audio/games/reveal.mp3'
import sndSuccess from '../assets/audio/games/success-single.mp3'
import sndSelect from '../assets/audio/games/select.mp3'

const CELL_COUNT = 40
const DRAW_COUNT = 10
const MAX_PICK = 10
const REVEAL_INTERVAL_MS = 210

const KENO_TABLE = {
  1:  [0, 3.5],
  2:  [0, 0, 15],
  3:  [0, 0, 0, 80],
  4:  [0, 0, 0, 12, 200],
  5:  [0, 0, 0, 4.5, 45, 450],
  6:  [0, 0, 0, 0, 6, 13, 450],
  7:  [0, 0, 0, 0, 3, 8, 13, 500],
  8:  [0, 0, 0, 0, 3, 6, 13, 40, 650],
  9:  [0, 0, 0, 0, 3, 8, 13, 40, 400, 800],
  10: [0, 0, 0, 0, 3.5, 8, 13, 40, 400, 650, 1000],
}

function multRow(nPicks) {
  return KENO_TABLE[Math.min(Math.max(nPicks, 1), 10)]
}

function displayKenoMult(raw) {
  if (!(raw > 0)) return 0
  return raw
}

function fmtMultDisplay(n) {
  if (n >= 1000) return `${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}x`
  return `${n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 1 })}x`
}

function shufflePick(arr, k) {
  const a = arr.slice()
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a.slice(0, k)
}

function playSound(src, volume = 0.55) {
  try {
    const a = new Audio(src)
    a.volume = volume
    a.play().catch(() => {})
  } catch (_) {}
}

export function mountKenoGame(opts) {
  const { gameHost, shell } = opts
  const numbers = Array.from({ length: CELL_COUNT }, (_, i) => i + 1)

  let selected = new Set()
  let drawn = new Set()
  let roundIdle = true

  const root = document.createElement('div')
  root.className = 'keno'
  root.innerHTML = `
    <div class="keno__grid" role="grid" aria-label="Keno board — pick up to ${MAX_PICK} numbers"></div>
    <div class="keno__bottom-wrap">
      <div class="keno__stats" data-keno-stats></div>
    </div>
  `

  const gridEl = root.querySelector('.keno__grid')
  const statsEl = root.querySelector('[data-keno-stats]')

  function tileHtml(n) {
    return `<div class="keno__tile-wrap">
      <div class="keno__tile-bg" aria-hidden="true"><img class="keno__bg-gem" src="${gemUrl}" alt="" /></div>
      <button type="button" class="keno__tile" data-n="${n}" aria-pressed="false" aria-label="Numer ${n}">
        <span class="keno__tile-num">${n}</span>
      </button>
    </div>`
  }
  gridEl.innerHTML = numbers.map(tileHtml).join('')

  function renderStatsRow() {
    statsEl.replaceChildren()
    const n = selected.size
    if (n === 0) {
      const hint = document.createElement('p')
      hint.className = 'keno__stats-hint'
      hint.textContent = 'Pick 1 to 10 tiles to start playing'
      statsEl.appendChild(hint)
      return
    }
    const row = multRow(n)
    for (let i = 0; i <= n; i += 1) {
      const pill = document.createElement('div')
      pill.className = 'keno__stat-pill'
      pill.dataset.hitCount = String(i)

      const count = document.createElement('span')
      count.className = 'keno__stat-count'
      const gem = document.createElement('img')
      gem.className = 'keno__gem keno__gem--xs'
      gem.src = gemUrl
      gem.alt = ''
      count.append(gem, document.createTextNode(`${i}x`))

      const mult = document.createElement('span')
      mult.className = 'keno__stat-mult'
      mult.textContent = fmtMultDisplay(displayKenoMult(row[i] ?? 0))

      pill.append(count, mult)
      statsEl.appendChild(pill)
    }
  }

  function getTileEl(n) {
    return gridEl.querySelector(`[data-n="${n}"]`)
  }

  function syncSelectionClasses() {
    root.querySelectorAll('.keno__tile').forEach((btn) => {
      const n = Number(btn.getAttribute('data-n'))
      const el = btn
      const isSel = selected.has(n)
      const isDrawn = drawn.has(n)
      if (roundIdle) {
        el.classList.toggle('keno__tile--hit', isSel && isDrawn)
        el.classList.toggle('keno__tile--stray', !isSel && isDrawn)
      }
      const revealed = el.classList.contains('keno__tile--hit') || el.classList.contains('keno__tile--stray')
      el.classList.toggle('keno__tile--selected', isSel && !revealed)
      el.setAttribute('aria-pressed', isSel ? 'true' : 'false')
    })
  }

  function revealTile(n) {
    const el = getTileEl(n)
    if (!el) return
    el.classList.remove('keno__tile--selected')
    if (selected.has(n)) {
      el.classList.add('keno__tile--hit')
      haptic('light')
      const gem = el.closest('.keno__tile-wrap')?.querySelector('.keno__bg-gem')
      if (gem) {
        gem.style.animation = 'none'
        void gem.offsetWidth
        gem.style.animation = 'keno-gem-pop 0.7s linear forwards'
      }
    } else {
      el.classList.add('keno__tile--stray')
    }
    el.setAttribute('aria-pressed', 'false')
  }

  function highlightMultAndHits(hitCount) {
    statsEl.querySelectorAll('.keno__stat-pill').forEach((pill) => {
      const c = Number(pill.getAttribute('data-hit-count'))
      pill.classList.toggle('keno__stat-pill--active', c === hitCount)
    })
  }

  function clearHighlights() {
    statsEl.querySelectorAll('.keno__stat-pill').forEach((p) => p.classList.remove('keno__stat-pill--active'))
  }

  function syncStatsHighlightIdle() {
    if (selected.size === 0 || drawn.size === 0) {
      clearHighlights()
      return
    }
    let h = 0
    selected.forEach((x) => {
      if (drawn.has(x)) h += 1
    })
    highlightMultAndHits(h)
  }

  function clearIdleRevealState() {
    if (drawn.size === 0) return
    drawn.clear()
    root.classList.add('keno--anim-reset')
    gridEl.querySelectorAll('.keno__bg-gem').forEach((gem) => {
      gem.style.animation = ''
    })
    syncSelectionClasses()
    void gridEl.offsetWidth
    root.classList.remove('keno--anim-reset')
    clearHighlights()
  }

  function onTileClick(n) {
    if (!roundIdle) return
    if (selected.has(n)) {
      selected.delete(n)
      haptic('light')
      clearIdleRevealState()
    } else if (selected.size < MAX_PICK) {
      selected.add(n)
      playSound(sndSelect, 0.45)
      haptic('selection')
    } else {
      haptic('warning')
      return
    }
    syncSelectionClasses()
    renderStatsRow()
    syncStatsHighlightIdle()
  }

  function prepareBoardForNewRound() {
    clearHighlights()
    root.classList.add('keno--anim-reset')
    drawn.clear()
    gridEl.querySelectorAll('.keno__tile').forEach((btn) => {
      btn.classList.remove('keno__tile--hit', 'keno__tile--stray')
    })
    gridEl.querySelectorAll('.keno__bg-gem').forEach((gem) => {
      gem.style.animation = ''
    })
    syncSelectionClasses()
    void gridEl.offsetWidth
    root.classList.remove('keno--anim-reset')
  }

  function randomPick() {
    if (!roundIdle) return
    haptic('medium')
    selected.clear()
    drawn.clear()
    gridEl.querySelectorAll('.keno__tile').forEach((btn) => {
      btn.classList.remove('keno__tile--hit', 'keno__tile--stray')
    })
    clearHighlights()
    shufflePick(numbers, MAX_PICK).forEach((n) => selected.add(n))
    playSound(sndSelect, 0.45)
    syncSelectionClasses()
    renderStatsRow()
    syncStatsHighlightIdle()
  }

  function clearBoard() {
    if (!roundIdle) return
    selected.clear()
    drawn.clear()
    haptic('light')
    gridEl.querySelectorAll('.keno__tile').forEach((btn) => {
      btn.classList.remove('keno__tile--hit', 'keno__tile--stray')
    })
    syncSelectionClasses()
    renderStatsRow()
    syncStatsHighlightIdle()
  }

  async function playRound() {
    if (!roundIdle) return
    if (selected.size === 0) {
      haptic('warning')
      shell.showGameError?.('Pick 1 to 10 numbers.')
      return
    }
    const bet = shell.getBetAmount()
    if (bet < 0.01) { haptic('warning'); return }

    shell.dismissResultModal?.()

    roundIdle = false
    playSound(sndBet, 0.55)
    haptic('medium')

    prepareBoardForNewRound()

    optimisticBalanceDelta(-bet)

    shell.setLoading?.(true)
    let drawnArr
    let newBalances = null
    let data
    try {
      data = await playKeno({
        selected: Array.from(selected),
        betAmount: bet,
        currency: getWalletCurrencyId(),
      })
    } catch (err) {
      optimisticBalanceDelta(bet)
      shell.setLoading?.(false)
      roundIdle = true
      haptic('warning')
      shell.showGameError?.(
        err instanceof ApiError ? err.message : 'Could not place bet',
      )
      return
    }
    if (!Array.isArray(data.drawn) || data.drawn.length === 0) {
      optimisticBalanceDelta(bet)
      shell.setLoading?.(false)
      roundIdle = true
      haptic('warning')
      return
    }
    drawnArr = data.drawn
    newBalances = data.balances ?? null
    shell.setLoading?.(false)
    shell.clearGameError?.()
    drawn = new Set(drawnArr)

    let hits = 0
    selected.forEach((n) => { if (drawn.has(n)) hits += 1 })

    const mult = Number(data.multiplier) || 0
    const payout = Number(data.payout) || 0
    const isWin = payout > 0
    const displayProfit = isWin ? payout - bet : 0

    const revealArr = Array.from(drawn).sort((a, b) => a - b)
    let hitsRevealedSoFar = 0
    revealArr.forEach((n, idx) => {
      window.setTimeout(() => {
        playSound(selected.has(n) ? sndSuccess : sndReveal, selected.has(n) ? 0.6 : 0.35)
        revealTile(n)
        if (selected.has(n)) {
          hitsRevealedSoFar += 1
          highlightMultAndHits(hitsRevealedSoFar)
        }

        if (idx === revealArr.length - 1) {
          highlightMultAndHits(hits)
          window.setTimeout(() => {
            shell.showResultModal(isWin, mult, isWin ? displayProfit : bet)
            if (isWin && newBalances != null) refreshBalance(newBalances)
            roundIdle = true
          }, 240)
        }
      }, idx * REVEAL_INTERVAL_MS)
    })
  }

  root.addEventListener('click', (e) => {
    const btn = e.target.closest('.keno__tile')
    if (!btn) return
    const n = Number(btn.getAttribute('data-n'))
    if (!Number.isFinite(n)) return
    onTileClick(n)
  })

  shell.el.addEventListener('click', (e) => {
    const t = e.target
    if (t.closest('[data-keno-random]')) { randomPick(); return }
    if (t.closest('[data-keno-clear]')) { clearBoard() }
  })

  gameHost.innerHTML = ''
  gameHost.appendChild(root)

  renderStatsRow()
  syncSelectionClasses()

  return {
    destroy() { root.remove() },
    playRound,
  }
}
