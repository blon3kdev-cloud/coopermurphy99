import { haptic } from '../lib/haptics.js'
import { getCurrencyIconSvg } from '../lib/currencyIcons.js'
import { subscribeWalletCurrency } from '../lib/walletCurrency.js'
import { openLoginIfGuest } from '../lib/betsApi.js'
import { CATEGORY_PAGE_BACK_ICON_HTML } from '../components/category-page-header/categoryPageBackIcon.js'
import { escapeHtml, sanitizeTrustedSvg } from '../lib/sanitizeHtml.js'
import {
  BJ_ICON_HIT,
  BJ_ICON_SPLIT,
  BJ_ICON_STAND,
} from './blackjackActionIcons.js'

const SHELL_GAME_TITLES = {
  keno: 'Keno',
  limbo: 'Limbo',
  dice: 'Dice',
  crash: 'Crash',
  blackjack: 'Blackjack',
  blitz: 'Blitz',
}

const DEMO_MAX_BET = 1_000_000
const MIN_BET = 0.01

function fmtPlnAmount(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '0.00'
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtBetFieldPln(n) {
  let v = Number(n)
  if (!Number.isFinite(v) || v < 0) v = 0
  v = Math.min(v, DEMO_MAX_BET)
  v = Math.round(v * 100) / 100
  return v.toFixed(2)
}

function fmtMult(n, keno = false) {
  const v = Number(n)
  if (keno && Number.isFinite(v)) {
    return `${v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 1 })}x`
  }
  return `${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}x`
}

function sidebarFieldsHtml(variant) {
  if (variant === 'keno') {
    return `
    <div class="crypto-casino__field">
      <div class="crypto-casino__keno-util-btns">
        <button type="button" class="crypto-casino__chip crypto-casino__chip--grow" data-keno-random>Random pick</button>
        <button type="button" class="crypto-casino__chip crypto-casino__chip--grow" data-keno-clear>Clear board</button>
      </div>
    </div>`
  }
  if (variant === 'dice') {
    return `
    <div class="crypto-casino__field casino-stat-field">
      <div class="casino-stat-field__label-row">
        <span class="casino-stat-field__label">Profit on win</span>
        <span class="crypto-casino__fiat-hint crypto-casino__fiat-hint--chip" data-crypto-profit-hint><span data-crypto-profit-hint-val>0.00</span> <span data-currency-icon></span></span>
      </div>
      <div class="casino-stat-field__box">
        <input type="text" class="casino-stat-field__input casino-stat-field__input--readonly" data-crypto-profit-val value="0,00" readonly tabindex="-1" aria-label="Profit on win" />
        <span class="casino-stat-field__suffix casino-stat-field__suffix--icon" aria-hidden="true"><span data-currency-icon></span></span>
      </div>
    </div>`
  }
  if (variant === 'limbo') {
    return `
    <div class="crypto-casino__field casino-stat-field">
      <label class="casino-stat-field__label" for="limbo-target-inp">Target multiplier</label>
      <div class="casino-stat-field__box">
        <input type="text" id="limbo-target-inp" class="casino-stat-field__input" data-limbo-sidebar-target value="2.00" inputmode="decimal" autocomplete="off" spellcheck="false" aria-label="Target multiplier" />
        <span class="casino-stat-field__suffix">×</span>
      </div>
    </div>`
  }
  if (variant === 'crash') {
    return `
    <div class="crypto-casino__field casino-stat-field">
      <label class="casino-stat-field__label" for="crash-cashout-inp">Cashout at<span class="casino-stat-field__opt">*</span></label>
      <div class="casino-stat-field__box">
        <input type="text" id="crash-cashout-inp" class="casino-stat-field__input casino-stat-field__input--unset" data-crash-sidebar-cashout value="Not set" inputmode="decimal" autocomplete="off" spellcheck="false" aria-label="Auto cashout multiplier (optional)" />
        <span class="casino-stat-field__suffix">×</span>
      </div>
    </div>`
  }
  if (variant === 'blitz') {
    return `
    <div class="crypto-casino__field casino-stat-field">
      <div class="casino-stat-field__label-row">
        <span class="casino-stat-field__label">Unique cards</span>
        <span class="crypto-casino__fiat-hint crypto-casino__fiat-hint--chip" data-blitz-mult>1.32x</span>
      </div>
      <div class="casino-stat-field__box casino-stat-field__box--stepper">
        <button type="button" class="casino-stat-field__step" data-blitz-unique-minus aria-label="Fewer unique cards">−</button>
        <input type="number" class="casino-stat-field__input casino-stat-field__input--center" data-blitz-unique value="5" min="5" max="36" aria-label="Unique cards target" />
        <button type="button" class="casino-stat-field__step" data-blitz-unique-plus aria-label="More unique cards">+</button>
      </div>
    </div>
    <div class="crypto-casino__field casino-stat-field">
      <div class="casino-stat-field__label-row">
        <span class="casino-stat-field__label">Profit</span>
        <span class="crypto-casino__fiat-hint crypto-casino__fiat-hint--chip" data-crypto-profit-hint><span data-crypto-profit-hint-val>0.00</span> <span data-currency-icon></span></span>
      </div>
      <div class="casino-stat-field__box">
        <input type="text" class="casino-stat-field__input casino-stat-field__input--readonly" data-crypto-profit-val value="0,00" readonly tabindex="-1" aria-label="Potential profit" />
        <span class="casino-stat-field__suffix casino-stat-field__suffix--icon" aria-hidden="true"><span data-currency-icon></span></span>
      </div>
    </div>`
  }
  if (variant === 'blackjack') {
    return `
    <div class="crypto-casino__bj-actions" data-bj-actions hidden>
      <div class="crypto-casino__bj-grid">
        <button type="button" class="crypto-casino__bj-btn crypto-casino__bj-btn--hit" data-bj-hit disabled>
          <span class="crypto-casino__bj-btn-icon">${BJ_ICON_HIT}</span>
          <span>Hit</span>
        </button>
        <button type="button" class="crypto-casino__bj-btn crypto-casino__bj-btn--stand" data-bj-stand disabled>
          <span class="crypto-casino__bj-btn-icon">${BJ_ICON_STAND}</span>
          <span>Stand</span>
        </button>
        <button type="button" class="crypto-casino__bj-btn" data-bj-split disabled>
          <span class="crypto-casino__bj-btn-icon">${BJ_ICON_SPLIT}</span>
          <span>Split</span>
        </button>
        <button type="button" class="crypto-casino__bj-btn" data-bj-double disabled>
          <span class="crypto-casino__bj-btn-icon crypto-casino__bj-btn-icon--text" aria-hidden="true">2x</span>
          <span>Double</span>
        </button>
      </div>
    </div>`
  }
  return ''
}

export function createCryptoCasinoShell(opts = {}) {
  const { onClose, shellVariant = 'default', onPlay, gameTitle } = opts
  const resolvedTitle =
    gameTitle || SHELL_GAME_TITLES[shellVariant] || 'Game'
  const el = document.createElement('div')
  el.className = 'crypto-casino'
  if (shellVariant !== 'default') el.classList.add(`crypto-casino--${shellVariant}`)

  el.innerHTML = `
${onClose ? `<div class="crypto-casino__topbar category-page-header--spacious-back">
  <div class="category-page-header__inner">
    <button type="button" class="category-page-header__back" data-crypto-back aria-label="Back to lobby">
      <span class="category-page-header__back-inner" aria-hidden="true">
        ${CATEGORY_PAGE_BACK_ICON_HTML}
      </span>
    </button>
    <h1 class="category-page-header__title">${escapeHtml(resolvedTitle)}</h1>
  </div>
</div>` : ''}
<div class="crypto-casino__upper">
<div class="crypto-casino__body">
  <aside class="crypto-casino__sidebar" aria-label="Bet">
    <div class="crypto-casino__field">
      <div class="crypto-casino__row-label">
        <span>Bet amount</span>
      </div>
      <div class="crypto-casino__bet-row">
        <div class="crypto-casino__input-wrap crypto-casino__input-wrap--bet">
          <input type="text" class="crypto-casino__input" data-crypto-bet value="10.00" inputmode="decimal" autocomplete="off" aria-label="Bet amount" />
          <span class="crypto-casino__input-suffix crypto-casino__input-suffix--icon" aria-hidden="true"><span data-currency-icon></span></span>
        </div>
        <div class="crypto-casino__chip-row">
          <button type="button" class="crypto-casino__chip" data-crypto-half>½</button>
          <button type="button" class="crypto-casino__chip" data-crypto-double>2x</button>
          <button type="button" class="crypto-casino__chip" data-crypto-max>Max</button>
        </div>
      </div>
    </div>
    ${sidebarFieldsHtml(shellVariant)}
    <div class="crypto-casino__actions">
      <p class="crypto-casino__err" data-crypto-err hidden></p>
      <button type="button" class="crypto-casino__btn crypto-casino__btn--primary" data-crypto-postaw>${shellVariant === 'blackjack' || shellVariant === 'blitz' ? 'Bet' : 'Place bet'}</button>
      <button type="button" class="crypto-casino__btn crypto-casino__btn--cashout" data-crypto-wyplac hidden>Cash out</button>
    </div>
  </aside>
  <div class="crypto-casino__play">
    <div class="crypto-casino__main">
      <div class="crypto-casino__game-view">
      <div class="crypto-casino__stage" data-crypto-game-host aria-label="Game area"></div>
<div class="crypto-casino-result" data-crypto-result hidden>
  <div class="crypto-casino-result__card" data-crypto-result-card>
    <div class="crypto-casino-result__mult" data-crypto-result-mult></div>
    <div class="crypto-casino-result__rule"></div>
    <div class="crypto-casino-result__amt-row">
      <span class="crypto-casino-result__amt" data-crypto-result-amt></span>
      <span class="crypto-casino-result__coin"><span data-currency-icon></span></span>
    </div>
  </div>
</div>
      </div>
    </div>
  </div>
</div>
</div>`

  let roundActive = false
  let betParsed = 1
  let walletSnap = { id: 'BTC', balancePln: 0 }
  let onBetChangeCb = null

  function notifyBetChange() {
    onBetChangeCb?.()
  }

  const betInput = el.querySelector('[data-crypto-bet]')
  const btnPostaw = el.querySelector('[data-crypto-postaw]')
  const errLine = el.querySelector('[data-crypto-err]')

  function clearGameError() {
    if (!errLine) return
    errLine.textContent = ''
    errLine.hidden = true
  }

  function showGameError(msg) {
    if (!errLine) return
    errLine.textContent = msg
    errLine.hidden = false
  }

  const resultRoot = el.querySelector('[data-crypto-result]')
  const resultCard = el.querySelector('[data-crypto-result-card]')
  const resultMult = el.querySelector('[data-crypto-result-mult]')
  const resultAmt  = el.querySelector('[data-crypto-result-amt]')
  const gameHost   = el.querySelector('[data-crypto-game-host]')

  function parseBet() {
    if (!betInput) return 0
    const raw = betInput.value.replace(/\s/g, '').replace(',', '.')
    const n = Number.parseFloat(raw)
    if (!Number.isFinite(n) || n < 0) return 0
    return Math.round(n * 100) / 100
  }

  function sanitizeBetInputWhileTyping() {
    if (!betInput) return
    const raw = betInput.value.replace(/\s/g, '').replace(',', '.')
    if (raw === '' || raw === '.') return
    let int = '', frac = '', seenDot = false
    for (let i = 0; i < raw.length; i++) {
      const c = raw[i]
      if (c >= '0' && c <= '9') {
        if (!seenDot) int += c
        else if (frac.length < 2) frac += c
      } else if (c === '.' && !seenDot) {
        seenDot = true
      }
    }
    let out = int
    if (seenDot) out += '.' + frac
    if (out !== betInput.value) betInput.value = out
  }

  function commitBetFieldFromBlur() {
    if (!betInput) return
    let n = parseBet()
    const empty = betInput.value.trim() === ''
    if (empty || !Number.isFinite(n)) n = 10
    if (n < MIN_BET) n = MIN_BET
    n = Math.min(n, DEMO_MAX_BET)
    betInput.value = fmtBetFieldPln(n)
    syncBetParsedFromInput()
    notifyBetChange()
  }

  function syncBetParsedFromInput() {
    betParsed = parseBet()
  }

  let resultAutoHideTimer = 0
  let resultHideAfterTransitionTimer = 0

  function showResult(won, mult, payoutDelta, opts = {}) {
    if (!resultRoot || !resultCard || !resultMult || !resultAmt) return
    const tie = opts.tie === true
    updateCurrencyIcons(walletSnap.id)
    window.clearTimeout(resultAutoHideTimer)
    window.clearTimeout(resultHideAfterTransitionTimer)
    resultAutoHideTimer = 0
    resultHideAfterTransitionTimer = 0
    resultCard.classList.toggle('crypto-casino-result__card--win', won && !tie)
    resultCard.classList.toggle('crypto-casino-result__card--loss', !won && !tie)
    resultCard.classList.toggle('crypto-casino-result__card--tie', tie)
    if (tie) {
      resultMult.textContent = 'Tie'
      resultAmt.textContent = 'Tie'
    } else {
      resultMult.textContent = won ? fmtMult(mult, shellVariant === 'keno') : 'Loss'
      resultAmt.textContent = won ? `+${fmtPlnAmount(payoutDelta)}` : `−${fmtPlnAmount(betParsed)}`
    }
    resultRoot.hidden = false
    void resultRoot.offsetHeight
    resultRoot.classList.add('crypto-casino-result--visible')
    haptic(tie ? 'light' : won ? 'success' : 'medium')
    resultAutoHideTimer = window.setTimeout(() => {
      resultAutoHideTimer = 0
      hideResult(false)
    }, 3200)
  }

  function hideResult(immediate = false) {
    window.clearTimeout(resultAutoHideTimer)
    resultAutoHideTimer = 0
    window.clearTimeout(resultHideAfterTransitionTimer)
    resultHideAfterTransitionTimer = 0
    if (!resultRoot) return
    resultRoot.classList.remove('crypto-casino-result--visible')
    if (immediate) {
      resultRoot.hidden = true
      return
    }
    resultHideAfterTransitionTimer = window.setTimeout(() => {
      resultHideAfterTransitionTimer = 0
      resultRoot.hidden = true
    }, 220)
  }

  function dismissResultModal() {
    hideResult(true)
  }

  el.addEventListener('click', (e) => {
    const t = e.target
    if (t.closest('[data-crypto-half]')) {
      haptic('light')
      if (!betInput || roundActive) return
      const v = Math.max(MIN_BET, Math.round(parseBet() * 0.5 * 100) / 100)
      betInput.value = fmtBetFieldPln(v)
      syncBetParsedFromInput()
      notifyBetChange()
      return
    }
    if (t.closest('[data-crypto-double]')) {
      haptic('light')
      if (!betInput || roundActive) return
      const v = Math.min(Math.round(parseBet() * 2 * 100) / 100, DEMO_MAX_BET)
      betInput.value = fmtBetFieldPln(v)
      syncBetParsedFromInput()
      notifyBetChange()
      return
    }
    if (t.closest('[data-crypto-max]')) {
      haptic('light')
      if (!betInput || roundActive) return
      const raw = Math.min(walletSnap.balancePln, DEMO_MAX_BET)
      betInput.value = fmtBetFieldPln(Math.max(MIN_BET, raw))
      syncBetParsedFromInput()
      notifyBetChange()
      return
    }
    if (t.closest('[data-crypto-postaw]')) {
      haptic('medium')
      clearGameError()
      if (t.closest('[data-crypto-postaw]:disabled')) return
      if ((shellVariant === 'keno' || shellVariant === 'limbo' || shellVariant === 'dice' || shellVariant === 'crash' || shellVariant === 'blackjack' || shellVariant === 'blitz') && onPlay) {
        if (openLoginIfGuest()) return
        if (roundActive) return
        betParsed = parseBet()
        if (betParsed < MIN_BET) { haptic('warning'); return }
        if (shellVariant === 'blitz') dismissResultModal()
        onPlay()
        syncBetParsedFromInput()
        return
      }
      return
    }
    if (t.closest('[data-crypto-back]')) {
      haptic('light')
      onClose?.()
    }
  })

  if (betInput) {
    betInput.addEventListener('input', () => {
      sanitizeBetInputWhileTyping()
      syncBetParsedFromInput()
      notifyBetChange()
    })
    betInput.addEventListener('focus', () => syncBetParsedFromInput())
    betInput.addEventListener('blur', () => commitBetFieldFromBlur())
  }

  function updateCurrencyIcons(currencyId) {
    const svg = getCurrencyIconSvg(currencyId)
    el.querySelectorAll('[data-currency-icon]').forEach((span) => {
      span.innerHTML = sanitizeTrustedSvg(svg)
    })
  }

  const unsubWallet = subscribeWalletCurrency((state) => {
    walletSnap = { id: state.id, balancePln: state.balanceRaw }
    updateCurrencyIcons(state.id)
    syncBetParsedFromInput()
  })

  return {
    el,
    gameHost,
    getBetAmount: () => parseBet(),
    onBetChange(cb) {
      onBetChangeCb = typeof cb === 'function' ? cb : null
    },
    getKenoDifficulty: () => 'medium',
    showResultModal: showResult,
    dismissResultModal,
    updateProfit(profit) {
      const valEl = el.querySelector('[data-crypto-profit-val]')
      if (valEl) valEl.value = fmtBetFieldPln(Math.max(0, profit))
      const hintVal = el.querySelector('[data-crypto-profit-hint-val]')
      if (hintVal) hintVal.textContent = fmtPlnAmount(Math.max(0, profit))
    },
    setRoundActive(on) {
      roundActive = Boolean(on)
      if (btnPostaw) btnPostaw.disabled = roundActive
      if (betInput) betInput.disabled = roundActive
    },
    setLoading(on) {
      if (!btnPostaw) return
      btnPostaw.classList.toggle('crypto-casino__btn--loading', on)
      if (!roundActive) btnPostaw.disabled = on
    },
    destroy() {
      unsubWallet()
      window.clearTimeout(resultAutoHideTimer)
      window.clearTimeout(resultHideAfterTransitionTimer)
    },
    clearGameError,
    showGameError,
  }
}
