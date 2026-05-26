import chipUrl from '../assets/currency/chip.png'

export { chipUrl }

/**
 * PLN balance display — matches API auth/wallet formatting:
 * thin space thousands, comma decimals (e.g. "12 345,67").
 */
export function formatPlnBalance(n) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '—'
  const sign = v < 0 ? '-' : ''
  const abs = Math.abs(v)
  const [intPart, dec] = abs.toFixed(2).split('.')
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',').replace(/,/g, '\u00a0')
  return `${sign}${grouped},${dec}`
}

/** Numeric platform balance / stake (no currency suffix). */
export function formatChipNumber(n, opts = {}) {
  const v = Number(n)
  if (!Number.isFinite(v)) return '0,00'
  const locale = opts.locale ?? 'en-US'
  const min = opts.minimumFractionDigits ?? 2
  const max = opts.maximumFractionDigits ?? 2
  return v.toLocaleString(locale, { minimumFractionDigits: min, maximumFractionDigits: max })
}

/** Remove legacy zł / PLN / $ suffixes from API strings. */
export function stripCurrencySuffix(s) {
  if (typeof s !== 'string') return s
  return s.replace(/\s*(zł|PLN|zl)\s*$/i, '').trim()
}

export function parseAmountFromDisplay(s) {
  if (typeof s === 'number') return s
  const cleaned = stripCurrencySuffix(String(s ?? ''))
    .replace(/\u00a0/g, ' ')
    .replace(/\s/g, '')
    .replace(',', '.')
  const n = Number(cleaned)
  return Number.isFinite(n) ? n : null
}
