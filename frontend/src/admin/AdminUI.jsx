import React, { useEffect, useMemo, useState } from 'react';
import { CurrencyAmount } from '../components/CurrencyAmount';

const ICONS = {
  dashboard: (
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      fill="currentColor"
      d="M2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 2 12ZM14.5237 8.24728C15.2702 8.04369 15.9552 8.72866 15.7516 9.47516L14.6322 13.5797C14.4924 14.0921 14.0921 14.4924 13.5797 14.6322L9.47516 15.7516C8.72866 15.9552 8.04369 15.2702 8.24728 14.5237L9.3667 10.4192C9.50645 9.90675 9.90675 9.50645 10.4192 9.3667L14.5237 8.24728Z"
    />
  ),
  users: (
    <>
      <path
        fill="currentColor"
        d="M13.501 6.5C13.501 4.01472 11.4863 2 9.00103 2C6.51575 2 4.50103 4.01472 4.50103 6.5C4.50103 8.98528 6.51575 11 9.00103 11C11.4863 11 13.501 8.98528 13.501 6.5Z"
      />
      <path
        fill="currentColor"
        d="M17.501 6.5C17.501 5.11929 16.3817 4 15.001 4C14.4487 4 14.001 3.55228 14.001 3C14.001 2.44772 14.4487 2 15.001 2C17.4863 2 19.501 4.01472 19.501 6.5C19.501 8.98528 17.4863 11 15.001 11C14.4487 11 14.001 10.5523 14.001 10C14.001 9.44772 14.4487 9 15.001 9C16.3817 9 17.501 7.88071 17.501 6.5Z"
      />
      <path
        fill="currentColor"
        d="M16.8126 19.7597C16.1479 20.5351 15.0993 21 14.001 21H4.001C2.90272 21 1.8541 20.5351 1.18942 19.7597C0.495057 18.9498 0.232544 17.7933 0.822256 16.6544C2.26755 13.8632 5.42359 12 9.001 12C12.5784 12 15.7345 13.8632 17.1797 16.6544C17.7695 17.7933 17.5069 18.9498 16.8126 19.7597Z"
      />
      <path
        fill="currentColor"
        d="M18.3352 12.5662C17.8146 12.3818 17.2431 12.6544 17.0587 13.1749C16.8743 13.6955 17.1468 14.267 17.6674 14.4514C19.5121 15.1048 20.9243 16.3999 21.584 17.9569C21.6869 18.1998 21.6429 18.4054 21.4722 18.5994C21.2782 18.8197 20.9227 19 20.5013 19C19.949 19 19.5013 19.4477 19.5013 20C19.5013 20.5523 19.949 21 20.5013 21C21.4606 21 22.3761 20.5993 22.9734 19.9209C23.5938 19.216 23.8612 18.205 23.4255 17.1766C22.5224 15.0451 20.6464 13.3848 18.3352 12.5662Z"
      />
    </>
  ),
  transactions: (
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      fill="currentColor"
      d="M1 8C1 5.79086 2.79086 4 5 4H19C21.2091 4 23 5.79086 23 8V16C23 18.2091 21.2091 20 19 20H5C2.79086 20 1 18.2091 1 16V8ZM4 6C3.44772 6 3 6.44772 3 7C3 7.55228 3.44772 8 4 8H5C5.55228 8 6 7.55228 6 7C6 6.44772 5.55228 6 5 6H4ZM12 9.5C10.6193 9.5 9.5 10.6193 9.5 12C9.5 13.3807 10.6193 14.5 12 14.5C13.3807 14.5 14.5 13.3807 14.5 12C14.5 10.6193 13.3807 9.5 12 9.5ZM19 16C18.4477 16 18 16.4477 18 17C18 17.5523 18.4477 18 19 18H20C20.5523 18 21 17.5523 21 17C21 16.4477 20.5523 16 20 16H19Z"
    />
  ),
  blik: (
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      fill="currentColor"
      d="M2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 2 12ZM12 5.5C12.5523 5.5 13 5.94772 13 6.5V7.12367C13.804 7.32711 14.5135 7.77457 14.9759 8.41405C15.2995 8.86159 15.199 9.48674 14.7515 9.81035C14.304 10.134 13.6788 10.0335 13.3552 9.58595C13.1379 9.28549 12.6534 9 12 9H11.7222C10.8274 9 10.5 9.54492 10.5 9.77778V9.8541C10.5 10.0514 10.6491 10.3826 11.1525 10.584L13.5902 11.5591C14.6572 11.9858 15.5 12.9386 15.5 14.1459C15.5 15.6189 14.323 16.6144 13 16.9091V17.5C13 18.0523 12.5523 18.5 12 18.5C11.4477 18.5 11 18.0523 11 17.5V16.8763C10.196 16.6729 9.4865 16.2254 9.02411 15.586C8.7005 15.1384 8.80096 14.5133 9.24851 14.1897C9.69605 13.866 10.3212 13.9665 10.6448 14.414C10.8621 14.7145 11.3466 15 12 15H12.1824C13.1298 15 13.5 14.4209 13.5 14.1459C13.5 13.9486 13.3509 13.6174 12.8475 13.416L10.4098 12.4409C9.34283 12.0142 8.5 11.0614 8.5 9.8541V9.77778C8.5 8.31377 9.68936 7.33904 11 7.07331V6.5C11 5.94772 11.4477 5.5 12 5.5Z"
    />
  ),
  codes: (
    <>
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        fill="currentColor"
        d="M2 5C2 4.44772 2.44772 4 3 4H13C13.5523 4 14 4.44772 14 5C14 5.55228 13.5523 6 13 6H3C2.44772 6 2 5.55228 2 5ZM17 5C17 4.44772 17.4477 4 18 4H21C21.5523 4 22 4.44772 22 5C22 5.55228 21.5523 6 21 6H18C17.4477 6 17 5.55228 17 5ZM2 12C2 11.4477 2.44772 11 3 11H8C8.55228 11 9 11.4477 9 12C9 12.5523 8.55228 13 8 13H3C2.44772 13 2 12.5523 2 12ZM12 12C12 11.4477 12.4477 11 13 11H21C21.5523 11 22 11.4477 22 12C22 12.5523 21.5523 13 21 13H13C12.4477 13 12 12.5523 12 12ZM2 19C2 18.4477 2.44772 18 3 18H10C10.5523 18 11 18.4477 11 19C11 19.5523 10.5523 20 10 20H3C2.44772 20 2 19.5523 2 19ZM14 19C14 18.4477 14.4477 18 15 18H21C21.5523 18 22 18.4477 22 19C22 19.5523 21.5523 20 21 20H15C14.4477 20 14 19.5523 14 19Z"
      />
    </>
  ),
  target: (
    <>
      <circle cx="12" cy="12" r="10" />
      <circle cx="12" cy="12" r="6" />
      <circle cx="12" cy="12" r="2" />
    </>
  ),
  bitcoin: (
    <>
      <path
        fill="currentColor"
        d="M10.7322 14.5875C11.6275 14.824 13.5841 15.3408 13.8952 14.0908C14.2139 12.8127 12.3163 12.3869 11.3904 12.1791C11.2869 12.1559 11.1956 12.1354 11.1208 12.1167L10.5183 14.532C10.5797 14.5472 10.6517 14.5663 10.7322 14.5875Z"
      />
      <path
        fill="currentColor"
        d="M11.5764 11.0582C12.3228 11.2574 13.951 11.6919 14.2346 10.5558C14.5242 9.39371 12.9418 9.04341 12.1689 8.87233C12.082 8.85308 12.0053 8.83611 11.9427 8.8205L11.3965 11.0111C11.4481 11.024 11.5086 11.0401 11.5764 11.0582Z"
      />
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        fill="currentColor"
        d="M9.57913 21.7006C14.9369 23.0365 20.3628 19.7763 21.6984 14.4191C23.034 9.06168 19.774 3.63486 14.4166 2.29925C9.06038 0.963634 3.6345 4.22423 2.29952 9.58198C0.963279 14.9388 4.22356 20.365 9.57913 21.7006ZM14.2027 8.05238C15.588 8.52956 16.6011 9.24487 16.402 10.5755C16.258 11.5495 15.718 12.0211 15.0011 12.1864C15.9855 12.6989 16.4864 13.4848 16.0092 14.8473C15.417 16.5395 14.0102 16.6823 12.1393 16.3282L11.6852 18.1479L10.588 17.8745L11.0361 16.0792C10.7518 16.0085 10.4612 15.9335 10.1618 15.8523L9.7121 17.656L8.61617 17.3826L9.07023 15.5595C8.9678 15.5333 8.86471 15.5064 8.7609 15.4793C8.60502 15.4387 8.44749 15.3976 8.28805 15.3576L6.86026 15.0017L7.40494 13.7458C7.40494 13.7458 8.21337 13.9608 8.20243 13.9448C8.51305 14.0217 8.65086 13.8192 8.70523 13.6842L9.42273 10.8077C9.44967 10.8141 9.47606 10.8208 9.50152 10.8271C9.51414 10.8303 9.52654 10.8334 9.53867 10.8364C9.49492 10.8189 9.45523 10.8077 9.4246 10.7999L9.93647 8.74643C9.94991 8.51331 9.8696 8.21925 9.42523 8.10832C9.44241 8.09675 8.62836 7.91019 8.62836 7.91019L8.92023 6.73833L10.4333 7.11614L10.4321 7.12176C10.6596 7.17833 10.894 7.23208 11.1327 7.28645L11.5824 5.48459L12.6789 5.75803L12.2383 7.52457C12.5327 7.59176 12.8289 7.65957 13.1174 7.73145L13.5549 5.97646L14.652 6.2499L14.2027 8.05238Z"
      />
    </>
  ),
  dice: (
    <path
      fillRule="evenodd"
      clipRule="evenodd"
      fill="currentColor"
      d="M9 21.0001C10.1046 21.0001 11 20.1047 11 19.0001L13 19.0001C13 20.1047 13.8954 21.0001 15 21.0001H17C18.1046 21.0001 19 20.1047 19 19.0001V16.8894C19.3295 16.5527 19.6258 16.183 19.8831 15.7854C20.2284 15.9239 20.6053 16.0001 20.999 16.0001C22.6558 16.0001 23.999 14.657 23.999 13.0001C23.999 12.4553 23.8528 11.9416 23.597 11.4994C23.3205 11.0213 22.7087 10.8579 22.2307 11.1345C21.7526 11.411 21.5892 12.0228 21.8658 12.5008C21.9503 12.6469 21.999 12.8163 21.999 13.0001C21.999 13.5524 21.5512 14.0001 20.999 14.0001C20.9017 14.0001 20.8082 13.9864 20.72 13.9609C20.9021 13.3394 21 12.6815 21 12.0001C21 8.13376 17.8663 5.0001 14 5.0001H10.0085C9.87889 4.83397 9.71111 4.64344 9.4999 4.44713C8.90931 3.89822 7.99073 3.31617 6.66148 3.09361C5.39073 2.88086 4.5 3.95345 4.5 5.00005V7.08361C3.98098 7.64381 3.60965 8.28657 3.32378 8.9351H3C1.89543 8.9351 1 9.83053 1 10.9351V14.0001C1 15.1047 1.89543 16.0001 3 16.0001H3.44811C3.88101 16.6316 4.37079 17.1193 5 17.551V19.0001C5 20.1047 5.89543 21.0001 7 21.0001H9ZM8.25 12.0001C8.94036 12.0001 9.5 11.4404 9.5 10.7501C9.5 10.0597 8.94036 9.50009 8.25 9.50009C7.55964 9.50009 7 10.0597 7 10.7501C7 11.4404 7.55964 12.0001 8.25 12.0001Z"
    />
  ),
  plus: (
    <>
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </>
  ),
  x: (
    <>
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </>
  ),
  arrowDown: (
    <>
      <line x1="12" y1="5" x2="12" y2="19" />
      <polyline points="19 12 12 19 5 12" />
    </>
  ),
  coins: (
    <>
      <ellipse cx="8" cy="6" rx="6" ry="3" />
      <path d="M2 6v6c0 1.66 2.69 3 6 3s6-1.34 6-3V6" />
      <path d="M2 12v4c0 1.66 2.69 3 6 3s6-1.34 6-3v-4" />
      <ellipse cx="16" cy="14" rx="6" ry="3" />
      <path d="M22 14v4c0 1.66-2.69 3-6 3" />
    </>
  ),
  trendingUp: (
    <>
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" />
      <polyline points="17 6 23 6 23 12" />
    </>
  ),
  percent: (
    <>
      <line x1="19" y1="5" x2="5" y2="19" />
      <circle cx="6.5" cy="6.5" r="2.5" />
      <circle cx="17.5" cy="17.5" r="2.5" />
    </>
  ),
  arrowLeft: (
    <>
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12 19 5 12 12 5" />
    </>
  ),
  chevronLeft: <polyline points="15 18 9 12 15 6" />,
  chevronRight: <polyline points="9 18 15 12 9 6" />,
  logout: (
    <>
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </>
  ),
  lock: (
    <>
      <rect x="3" y="11" width="18" height="11" rx="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </>
  ),
  check: <polyline points="20 6 9 17 4 12" />,
  refund: (
    <>
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
    </>
  ),
  image: (
    <>
      <path
        fill="currentColor"
        d="M18.9472 1.89431C18.763 1.52579 18.237 1.52579 18.0528 1.89431L17.0745 3.85082C17.0262 3.94758 16.9477 4.02604 16.8509 4.07442L14.8944 5.05267C14.5259 5.23693 14.5259 5.76284 14.8944 5.9471L16.8509 6.92535C16.9477 6.97373 17.0262 7.05219 17.0745 7.14896L18.0528 9.10546C18.237 9.47398 18.763 9.47398 18.9472 9.10546L19.9255 7.14896C19.9738 7.05219 20.0523 6.97373 20.1491 6.92535L22.1056 5.9471C22.4741 5.76284 22.4741 5.23693 22.1056 5.05267L20.1491 4.07442C20.0523 4.02604 19.9738 3.94758 19.9255 3.85082L18.9472 1.89431Z"
      />
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        fill="currentColor"
        d="M5 6.99989C5 5.89532 5.89543 4.99989 7 4.99989H11C11.5523 4.99989 12 4.55217 12 3.99989C12 3.4476 11.5523 2.99989 11 2.99989H7C4.79086 2.99989 3 4.79075 3 6.99989V16.9999C3 19.209 4.79086 20.9999 7 20.9999H17C19.2091 20.9999 21 19.209 21 16.9999V12.9999C21 12.4476 20.5523 11.9999 20 11.9999C19.4477 11.9999 19 12.4476 19 12.9999V16.9999C19 18.1045 18.1046 18.9999 17 18.9999H16.9C16.4367 16.7176 14.419 14.9999 12 14.9999C9.58104 14.9999 7.56329 16.7176 7.10002 18.9999H7C5.89543 18.9999 5 18.1045 5 16.9999V6.99989Z"
      />
      <path
        fill="currentColor"
        d="M12 7.49976C10.3431 7.49976 9 8.8429 9 10.4998C9 12.1566 10.3431 13.4998 12 13.4998C13.6569 13.4998 15 12.1566 15 10.4998C15 8.8429 13.6569 7.49976 12 7.49976Z"
      />
    </>
  ),
  upload: (
    <>
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
    </>
  ),
};

const FILLED_ICONS = new Set([
  'dashboard',
  'users',
  'transactions',
  'blik',
  'codes',
  'image',
  'bitcoin',
  'dice',
]);

export function Icon({ name, size = 18, filled }) {
  const isFilled = filled ?? FILLED_ICONS.has(name);
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={isFilled ? 'none' : 'currentColor'}
      strokeWidth={isFilled ? 0 : 1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  );
}

export function Page({ title, action, children }) {
  return (
    <div className="ad-page">
      <div className="ad-page__head">
        <h1 className="ad-page__title">{title}</h1>
        {action && <div className="ad-page__action">{action}</div>}
      </div>
      {children}
    </div>
  );
}

export function Card({ title, action, padded = false, children }) {
  return (
    <section className="ad-card">
      {(title || action) && (
        <header className="ad-card__head">
          {title && <h2 className="ad-card__title">{title}</h2>}
          {action && <div>{action}</div>}
        </header>
      )}
      <div className={padded ? 'ad-card__body ad-card__body--padded' : 'ad-card__body'}>
        {children}
      </div>
    </section>
  );
}

export function StatTile({ value, label, icon, tone = 'cyan' }) {
  return (
    <div className={`ad-stat ad-stat--${tone}`}>
      <div className="ad-stat__main">
        <div className="ad-stat__value">{value}</div>
        <div className="ad-stat__label">{label}</div>
      </div>
      <div className="ad-stat__icon" aria-hidden="true">
        <Icon name={icon} size={56} />
      </div>
    </div>
  );
}

export function DataTable({ columns, rows, onRowClick, empty = 'No data', pageSize }) {
  const [page, setPage] = useState(1);
  const total = rows.length;
  const pages = pageSize ? Math.max(1, Math.ceil(total / pageSize)) : 1;

  useEffect(() => {
    setPage((p) => Math.min(p, pages));
  }, [pages]);

  const visible = useMemo(() => {
    if (!pageSize) return rows;
    const start = (page - 1) * pageSize;
    return rows.slice(start, start + pageSize);
  }, [rows, page, pageSize]);

  return (
    <>
      <div className="ad-table-wrap">
        <table className="ad-table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} style={c.width ? { width: c.width } : undefined}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="ad-table__empty">
                  {empty}
                </td>
              </tr>
            ) : (
              visible.map((r) => (
                <tr
                  key={r.id ?? r.key}
                  className={onRowClick ? 'ad-table__row--clickable' : undefined}
                  onClick={onRowClick ? () => onRowClick(r) : undefined}
                >
                  {columns.map((c) => (
                    <td key={c.key}>{c.render ? c.render(r) : r[c.key]}</td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {pageSize && total > 0 && (
        <Pagination page={page} pages={pages} pageSize={pageSize} total={total} onChange={setPage} />
      )}
    </>
  );
}

function Pagination({ page, pages, pageSize, total, onChange }) {
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);
  return (
    <div className="ad-pagination">
      <span className="ad-pagination__info">
        Showing <strong>{start}–{end}</strong> of <strong>{total}</strong>
      </span>
      <div className="ad-pagination__controls">
        <button
          type="button"
          className="ad-pagination__btn"
          disabled={page <= 1}
          onClick={() => onChange(page - 1)}
          aria-label="Previous page"
        >
          <Icon name="chevronLeft" size={16} />
        </button>
        <span className="ad-pagination__page">
          Page {page} of {pages}
        </span>
        <button
          type="button"
          className="ad-pagination__btn"
          disabled={page >= pages}
          onClick={() => onChange(page + 1)}
          aria-label="Next page"
        >
          <Icon name="chevronRight" size={16} />
        </button>
      </div>
    </div>
  );
}

export function LiveIndicator({ label = 'Live' }) {
  return (
    <span className="ad-live" title="Refreshes automatically">
      <span className="ad-live__spinner" aria-hidden="true" />
      {label}
    </span>
  );
}

export function Toolbar({ children }) {
  return <div className="ad-toolbar">{children}</div>;
}

export function Field({ label, children }) {
  return (
    <label className="ad-field">
      <span className="ad-field__label">{label}</span>
      {children}
    </label>
  );
}

export function Modal({ open, onClose, title, children, wide = false }) {
  if (!open) return null;
  return (
    <div className="ad-modal" role="dialog" aria-modal="true" onClick={onClose}>
      <div
        className={
          wide ? 'ad-modal__panel ad-modal__panel--wide' : 'ad-modal__panel'
        }
        onClick={(e) => e.stopPropagation()}
      >
        <header className="ad-modal__head">
          <h2>{title}</h2>
          <button
            type="button"
            className="ad-modal__close"
            onClick={onClose}
            aria-label="Close"
          >
            <Icon name="x" size={18} />
          </button>
        </header>
        <div className="ad-modal__body">{children}</div>
      </div>
    </div>
  );
}

export function Segmented({ value, onChange, options }) {
  return (
    <div className="ad-seg" role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="tab"
          aria-selected={value === o.value}
          className={
            value === o.value ? 'ad-seg__btn ad-seg__btn--active' : 'ad-seg__btn'
          }
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Badge({ tone = 'gray', children }) {
  return <span className={`ad-badge ad-badge--${tone}`}>{children}</span>;
}

export function DetailList({ items }) {
  return (
    <dl className="ad-detail">
      {items.map(([k, v]) => (
        <div className="ad-detail__row" key={k}>
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export const fmt = {
  money: (n) => (
    <CurrencyAmount value={n} size={14} className="currency-amount--admin" decimals={2} />
  ),
  number: (n) => Number(n).toLocaleString(),
  percent: (n) => Number(n).toFixed(2) + '%',
};
