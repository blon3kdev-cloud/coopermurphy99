import { isUserSessionActive } from './betsApi'
import { wallet } from './api'
import { formatPlnBalance } from './currencyFormat.js'

/** @typedef {'PLN'} WalletCurrencyId */

/** @type {WalletCurrencyId} */
let selected = 'PLN'

const listeners = new Set()
let cached = { balance: '—', balanceRaw: 0, navbarBalance: '—' }

function emit() {
  listeners.forEach((f) => f())
}

function applyKnownBalance(pln) {
  const formatted = formatPlnBalance(pln)
  cached = {
    balance: formatted,
    balanceRaw: pln,
    navbarBalance: formatted,
  }
}

/** @returns {WalletCurrencyId} */
export function getWalletCurrencyId() {
  return selected
}

/** @param {WalletCurrencyId} id */
export function setWalletCurrency(id) {
  if (id === selected) return
  selected = id
  emit()
}

/**
 * @param {Record<string, number> | null | undefined} [known]
 */
export function resetWalletCache() {
  cached = { balance: '—', balanceRaw: 0, navbarBalance: '—' }
  emit()
}

/** Optimistic balance tweak before server confirms (e.g. bet placement). */
export function optimisticBalanceDelta(deltaPln) {
  if (cached.balanceRaw <= 0 && deltaPln < 0) return;
  applyKnownBalance(Math.max(0, cached.balanceRaw + deltaPln));
  emit();
}

export async function refreshBalance(known) {
  if (known?.PLN != null) {
    applyKnownBalance(known.PLN)
  } else if (isUserSessionActive()) {
    try {
      const data = await wallet.getBalance()
      if (data?.balanceRaw != null) {
        applyKnownBalance(data.balanceRaw)
      }
    } catch {
      /* keep last cached */
    }
  }
  emit()
}

/**
 * @returns {{ id: WalletCurrencyId; label: string; balance: string; balanceRaw: number }}
 */
export function getWalletState() {
  return {
    id: selected,
    label: selected,
    balance: cached.balance,
    balanceRaw: cached.balanceRaw,
    navbarBalance: cached.navbarBalance,
  }
}

/**
 * @param {(s: ReturnType<typeof getWalletState>) => void} fn
 * @returns {() => void} unsubscribe
 */
export function subscribeWalletCurrency(fn) {
  const wrap = () => fn(getWalletState())
  listeners.add(wrap)
  wrap()
  if (isUserSessionActive()) refreshBalance()
  return () => listeners.delete(wrap)
}
