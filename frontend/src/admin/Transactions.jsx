import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import AdminContentLoader from './AdminContentLoader';
import { Page, Card, DataTable, Toolbar, Badge, fmt } from './AdminUI';
import { useAdminQuery } from './useAdminQuery';
import { admin } from '../lib/api';

const STATUS_TONE = {
  completed: 'green',
  pending: 'orange',
  failed: 'red',
  refunded: 'gray',
};

const DEPOSIT_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'user', label: 'User' },
  {
    key: 'method',
    label: 'Method',
    render: (r) => (
      <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <Badge tone={r.method === 'blik' ? 'purple' : 'gray'}>{r.method || 'crypto'}</Badge>
        {r.blikManual && <Badge tone="orange">BLIK code</Badge>}
      </span>
    ),
  },
  { key: 'asset', label: 'Asset', render: (r) => <Badge tone="gray">{r.asset}</Badge> },
  {
    key: 'amount',
    label: 'Amount',
    render: (r) =>
      r.amountPln != null ? fmt.money(r.amountPln) : `${r.amountCrypto} ${r.asset}`,
  },
  {
    key: 'address',
    label: 'Address / Code',
    render: (r) => (
      <span className="ad-muted" title={r.address || r.manualCode}>
        {r.manualCode
          ? `Code: ${r.manualCode}`
          : r.address
            ? `${r.address.slice(0, 10)}…`
            : '—'}
      </span>
    ),
  },
  {
    key: 'matchedWithdraw',
    label: 'Match',
    render: (r) =>
      r.fundsWithdrawal || r.matchedWithdraw ? (
        <Badge tone="purple">#{r.matchedWithdraw}</Badge>
      ) : (
        <span className="ad-muted">—</span>
      ),
  },
  {
    key: 'status',
    label: 'Status',
    render: (r) => <Badge tone={STATUS_TONE[r.status] || 'gray'}>{r.status}</Badge>,
  },
  { key: 'date', label: 'Date' },
];

const WITHDRAW_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'user', label: 'User' },
  {
    key: 'method',
    label: 'Method',
    render: (r) => <Badge tone={r.method === 'blik' ? 'purple' : 'gray'}>{r.method || 'crypto'}</Badge>,
  },
  { key: 'asset', label: 'Asset', render: (r) => <Badge tone="gray">{r.asset}</Badge> },
  {
    key: 'amount',
    label: 'Amount',
    render: (r) =>
      r.amountPln != null ? fmt.money(r.amountPln) : `${r.amountCrypto} ${r.asset}`,
  },
  {
    key: 'progress',
    label: 'Filled',
    render: (r) =>
      r.method === 'blik' ? (
        <span className="ad-muted">{r.blikStatus || '—'}</span>
      ) : (
        `${r.filled} / ${r.amountCrypto}`
      ),
  },
  {
    key: 'destination',
    label: 'Destination',
    render: (r) => (
      <span className="ad-muted" title={r.destination}>
        {r.destination ? `${String(r.destination).slice(0, 14)}` : '—'}
      </span>
    ),
  },
  {
    key: 'status',
    label: 'Status',
    render: (r) => <Badge tone={STATUS_TONE[r.status] || 'gray'}>{r.status}</Badge>,
  },
  { key: 'date', label: 'Date' },
];

function withdrawActionsColumn(onRefund, refundBusy) {
  return {
    key: 'actions',
    label: '',
    render: (r) => {
      if (r.status === 'refunded') {
        return <span className="ad-muted">Refunded</span>;
      }
      if (r.status !== 'pending') {
        return <span className="ad-muted">—</span>;
      }
      const busy = refundBusy === r.id;
      return (
        <button
          type="button"
          className="ad-btn ad-btn--ghost ad-btn--sm"
          disabled={busy}
          onClick={() => onRefund(r.id)}
        >
          {busy ? '…' : 'Refund'}
        </button>
      );
    },
  };
}

function TxTab({ active, label, onClick }) {
  return (
    <button
      type="button"
      className={`ad-tabs__btn${active ? ' ad-tabs__btn--active' : ''}`}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

export default function Transactions() {
  const navigate = useNavigate();
  const [tab, setTab] = useState('deposits');
  const [platform, setPlatform] = useState('all');
  const [status, setStatus] = useState('all');
  const [minAmount, setMinAmount] = useState('');
  const [refundBusy, setRefundBusy] = useState(null);
  const { loading, data, setData } = useAdminQuery(
    () =>
      Promise.all([admin.getTransactions(), admin.getAdminSettings()]).then(
        ([tx, settings]) => ({
          transactions: Array.isArray(tx) ? tx : [],
          blikActive: Boolean(settings?.blikActive),
        }),
      ),
    [],
  );
  const transactions = data?.transactions ?? [];
  const blikActive = Boolean(data?.blikActive);

  const toggleBlik = async () => {
    const next = !blikActive;
    const s = await admin.patchAdminSettings({ blikActive: next });
    setData((prev) =>
      prev
        ? { ...prev, blikActive: Boolean(s?.blikActive) }
        : { transactions: [], blikActive: Boolean(s?.blikActive) },
    );
    if (Boolean(s?.blikActive)) navigate('/admin/blik');
  };

  const rows = useMemo(() => {
    const kind = tab === 'deposits' ? 'deposit' : 'withdraw';
    return transactions.filter((t) => {
      if (t.type !== kind) return false;
      if (platform !== 'all' && t.platform !== platform) return false;
      if (status !== 'all' && t.status !== status) return false;
      if (minAmount && t.amount < Number(minAmount)) return false;
      return true;
    });
  }, [transactions, tab, platform, status, minAmount]);

  const refreshTransactions = () =>
    admin.getTransactions().then((tx) => {
      setData((prev) =>
        prev ? { ...prev, transactions: Array.isArray(tx) ? tx : [] } : prev,
      );
    });

  const handleRefund = async (id) => {
    setRefundBusy(id);
    try {
      await admin.refundWithdrawal(id);
      await refreshTransactions();
    } finally {
      setRefundBusy(null);
    }
  };

  const columns =
    tab === 'deposits'
      ? DEPOSIT_COLUMNS
      : [...WITHDRAW_COLUMNS, withdrawActionsColumn(handleRefund, refundBusy)];

  return (
    <Page title="Transactions">
      <AdminContentLoader loading={loading}>
      <Card>
        <Toolbar>
          <button
            type="button"
            className={`ad-btn ${blikActive ? 'ad-btn--success' : 'ad-btn--primary'}`}
            onClick={toggleBlik}
          >
            {blikActive ? 'BLIK active' : 'Enable BLIK'}
          </button>
          {blikActive && (
            <button
              type="button"
              className="ad-btn ad-btn--ghost"
              onClick={() => navigate('/admin/blik')}
            >
              BLIK codes panel →
            </button>
          )}
        </Toolbar>
        <p className="ad-muted" style={{ margin: '12px 0 0', fontSize: '0.9rem' }}>
          {blikActive
            ? 'BLIK mode is on: users without a matching withdrawal deposit with a 6-digit code. Redeem them in the BLIK panel.'
            : 'Off: when there is no withdrawal for the same amount, BLIK code deposits are unavailable.'}
        </p>
      </Card>

      <div className="ad-stack-gap">
        <Card>
          <div className="ad-tabs">
            <TxTab
              active={tab === 'deposits'}
              label="Deposits"
              onClick={() => setTab('deposits')}
            />
            <TxTab
              active={tab === 'withdrawals'}
              label="Withdrawals"
              onClick={() => setTab('withdrawals')}
            />
          </div>
          <Toolbar>
            <select
              className="ad-select"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              <option value="all">All platforms</option>
              <option value="discord">Discord</option>
              <option value="telegram">Telegram</option>
            </select>
            <select
              className="ad-select"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
            >
              <option value="all">All statuses</option>
              <option value="completed">Completed</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
              <option value="refunded">Refunded</option>
            </select>
            <input
              className="ad-input"
              type="number"
              placeholder="Min amount"
              value={minAmount}
              onChange={(e) => setMinAmount(e.target.value)}
            />
          </Toolbar>
          <DataTable
            columns={columns}
            rows={rows}
            empty={`No ${tab} match your filters`}
            pageSize={8}
          />
        </Card>
      </div>
      </AdminContentLoader>
    </Page>
  );
}
