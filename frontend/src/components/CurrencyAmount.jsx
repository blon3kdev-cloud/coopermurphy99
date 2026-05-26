import { chipUrl, formatChipNumber, parseAmountFromDisplay, stripCurrencySuffix } from '../lib/currencyFormat'
import './CurrencyAmount.css'

/**
 * Platform balance amount with chip icon (replaces PLN / zł / $ labels).
 * @param {{ value?: number | string; amount?: number | string; prefix?: string; className?: string; size?: number; decimals?: number }} props
 */
export function CurrencyAmount({ value, amount, prefix = '', className = '', size = 18, decimals = 2 }) {
  const raw = value ?? amount
  const num = typeof raw === 'number' ? raw : parseAmountFromDisplay(raw)
  const text =
    typeof raw === 'string' && num == null
      ? stripCurrencySuffix(raw)
      : formatChipNumber(num ?? 0, {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        })

  return (
    <span className={`currency-amount ${className}`.trim()}>
      {prefix ? <span className="currency-amount__prefix">{prefix}</span> : null}
      <span className="currency-amount__value">{text}</span>
      <img
        src={chipUrl}
        alt=""
        className="currency-amount__chip"
        width={size}
        height={size}
        decoding="async"
        draggable={false}
        aria-hidden
      />
    </span>
  )
}
