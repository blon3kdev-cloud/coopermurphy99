import { toast } from 'react-toastify';
import { CurrencyAmount } from '../components/CurrencyAmount';

const defaultOpts = { autoClose: 4000 };

/** @param {string} message */
export function toastSuccess(message) {
  toast.success(message, defaultOpts);
}

/** @param {string} message */
export function toastError(message) {
  toast.error(message, defaultOpts);
}

/** @param {string} message */
export function toastInfo(message) {
  toast.info(message, defaultOpts);
}

/** @param {number} amountPln */
export function formatPlnToast(amountPln) {
  const n = Number(amountPln);
  if (!Number.isFinite(n)) return '0,00';
  return n.toFixed(2).replace('.', ',');
}

/** Toast with chip icon for a credited amount. */
export function toastChipCredit(message, amountPln) {
  toast.success(
    <span className="toast-chip-credit">
      {message}{' '}
      <CurrencyAmount value={amountPln} prefix="+" size={16} />
    </span>,
    defaultOpts,
  );
}
