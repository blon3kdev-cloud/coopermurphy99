import React, { useCallback, useEffect, useState } from 'react';
import { useVisibilityInterval } from '../hooks/useVisibilityInterval';
import { Link, useNavigate } from 'react-router-dom';
import AdminContentLoader from './AdminContentLoader';
import { Page, Card, Badge, fmt } from './AdminUI';
import { admin } from '../lib/api';
import './BlikPanel.css';

function BlikCodeCard({ row, busy, onRedeem }) {
  return (
    <article className={`blik-card${busy ? ' blik-card--busy' : ''}`}>
      <div className="blik-card__head">
        <Badge tone="purple">BLIK</Badge>
        <span className="blik-card__id">#{row.id}</span>
        <Badge tone="orange">Pending</Badge>
      </div>
      <div className="blik-card__code" aria-label="BLIK code">
        {row.code}
      </div>
      <dl className="blik-card__meta">
        <div>
          <dt>User</dt>
          <dd>{row.user}</dd>
        </div>
        <div>
          <dt>Amount</dt>
          <dd>{fmt.money(row.amountPln)}</dd>
        </div>
        <div>
          <dt>Platform</dt>
          <dd>{row.platform}</dd>
        </div>
        <div>
          <dt>Time</dt>
          <dd>{row.date}</dd>
        </div>
      </dl>
      <div className="blik-card__actions">
        <button
          type="button"
          className="ad-btn ad-btn--success"
          disabled={busy}
          onClick={() => onRedeem(row.id, true)}
        >
          Redeemed
        </button>
        <button
          type="button"
          className="ad-btn ad-btn--danger"
          disabled={busy}
          onClick={() => onRedeem(row.id, false)}
        >
          Reject
        </button>
      </div>
    </article>
  );
}

export default function BlikPanel() {
  const navigate = useNavigate();
  const [blikActive, setBlikActive] = useState(false);
  const [codes, setCodes] = useState([]);
  const [redeemBusy, setRedeemBusy] = useState(null);
  const [initialLoading, setInitialLoading] = useState(true);

  const refresh = useCallback((opts = {}) => {
    const { silent = false } = opts;
    if (!silent) setInitialLoading(true);
    return Promise.all([
      admin.getAdminSettings(),
      admin.getPendingBlikCodes(),
    ])
      .then(([s, data]) => {
        setBlikActive(Boolean(s?.blikActive));
        setCodes(Array.isArray(data) ? data : []);
      })
      .finally(() => {
        if (!silent) setInitialLoading(false);
      });
  }, []);

  useVisibilityInterval(() => refresh({ silent: true }), 5000, true);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const turnOff = async () => {
    const s = await admin.patchAdminSettings({ blikActive: false });
    setBlikActive(Boolean(s?.blikActive));
    navigate('/admin/transactions');
  };

  const handleRedeem = async (depositId, success) => {
    setRedeemBusy(depositId);
    try {
      await admin.redeemBlikCode(depositId, success);
      refresh();
    } finally {
      setRedeemBusy(null);
    }
  };

  if (initialLoading) {
    return (
      <Page title="BLIK">
        <AdminContentLoader loading minHeight="320px">
          <div />
        </AdminContentLoader>
      </Page>
    );
  }

  if (!blikActive) {
    return (
      <Page title="BLIK">
        <Card>
          <p className="ad-muted">
            BLIK mode is off. Enable it on the Transactions page — users without a matching
            withdrawal can then deposit with a BLIK code.
          </p>
          <Link to="/admin/transactions" className="ad-btn ad-btn--primary">
            ← Transactions
          </Link>
        </Card>
      </Page>
    );
  }

  return (
    <Page title="BLIK — codes to redeem">
      <div className="blik-panel__status">
        <span className="blik-panel__pulse" aria-hidden />
        <strong>BLIK mode active</strong>
        <span className="ad-muted">— code deposits enabled</span>
        <button type="button" className="ad-btn ad-btn--ghost ad-btn--sm" onClick={turnOff}>
          Turn off
        </button>
        <Link to="/admin/transactions" className="ad-btn ad-btn--ghost ad-btn--sm">
          Transactions
        </Link>
      </div>

      {codes.length === 0 ? (
        <Card>
          <p className="blik-panel__empty">No codes to redeem. Refreshing every 5 s…</p>
        </Card>
      ) : (
        <div className="blik-panel__grid">
          {codes.map((row) => (
            <BlikCodeCard
              key={row.id}
              row={row}
              busy={redeemBusy === row.id}
              onRedeem={handleRedeem}
            />
          ))}
        </div>
      )}
    </Page>
  );
}
