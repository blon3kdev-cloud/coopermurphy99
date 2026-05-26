import { chipUrl } from './currencyFormat.js'

/**
 * Single platform “currency” mark (casino shell, wallet UI, etc.).
 * Krypto bet cards use their own icons in `KryptoBetCard.jsx`.
 * @param {string} [_id] legacy wallet id — ignored; chip is always shown
 * @returns {string} HTML img tag
 */
export function getCurrencyIconSvg(_id) {
  return `<img class="currency-ico currency-ico--chip" src="${chipUrl}" width="20" height="20" alt="" decoding="async" aria-hidden="true" />`
}
