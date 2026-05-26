import React, { useEffect, useState } from 'react';
import AdminContentLoader from './AdminContentLoader';
import {
  Page,
  Card,
  DataTable,
  Modal,
  Field,
  Badge,
  Icon,
  fmt,
} from './AdminUI';
import { useAdminQuery } from './useAdminQuery';
import { admin } from '../lib/api';

const STATUS_TONE = {
  active: 'green',
  exhausted: 'gray',
};

const COLUMNS = [
  { key: 'code', label: 'Code' },
  { key: 'label', label: 'Label' },
  {
    key: 'kind',
    label: 'Type',
    render: (r) => <Badge tone="gray">{r.kind}</Badge>,
  },
  { key: 'amount', label: 'Amount', render: (r) => fmt.money(r.amount) },
  {
    key: 'uses',
    label: 'Uses',
    render: (r) => `${r.usesCount} / ${r.maxUses}`,
  },
  {
    key: 'status',
    label: 'Status',
    render: (r) => (
      <Badge tone={STATUS_TONE[r.status] || 'orange'}>{r.status}</Badge>
    ),
  },
  { key: 'createdAt', label: 'Created' },
];

export default function Codes() {
  const { loading, data: codes, reload } = useAdminQuery(
    () => admin.getCodes().then((data) => (Array.isArray(data) ? data : [])),
    [],
  );
  const {
    loading: dailyLoading,
    data: dailySettings,
    setData: setDailySettings,
  } = useAdminQuery(() => admin.getDailyCodeSettings(), []);
  const codeRows = codes ?? [];
  const [adding, setAdding] = useState(false);
  const [amount, setAmount] = useState('10');
  const [maxUses, setMaxUses] = useState('100');
  const [label, setLabel] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [lastCreated, setLastCreated] = useState(null);
  const [dailyAmount, setDailyAmount] = useState('');
  const [dailyMaxUses, setDailyMaxUses] = useState('');
  const [dailySaving, setDailySaving] = useState(false);
  const [dailyError, setDailyError] = useState('');
  const [dailySaved, setDailySaved] = useState(false);

  useEffect(() => {
    if (!dailySettings) return;
    setDailyAmount(String(dailySettings.amountPln ?? ''));
    setDailyMaxUses(String(dailySettings.maxUses ?? ''));
  }, [dailySettings]);

  const copyCode = async (code) => {
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      /* ignore */
    }
  };

  const saveDailySettings = async (e) => {
    e.preventDefault();
    setDailyError('');
    setDailySaved(false);
    const amt = Number(dailyAmount);
    const max = Number(dailyMaxUses);
    if (!amt || amt <= 0) {
      setDailyError('Enter a valid amount.');
      return;
    }
    if (!max || max < 1) {
      setDailyError('Global uses must be at least 1.');
      return;
    }
    setDailySaving(true);
    try {
      const updated = await admin.patchDailyCodeSettings({
        amountPln: amt,
        maxUses: max,
      });
      setDailySettings(updated);
      setDailySaved(true);
    } catch (err) {
      setDailyError(err?.message || 'Could not save daily settings.');
    } finally {
      setDailySaving(false);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    const amt = Number(amount);
    const max = Number(maxUses);
    if (!amt || amt <= 0) {
      setError('Enter a valid amount.');
      return;
    }
    if (!max || max < 1) {
      setError('Max uses must be at least 1.');
      return;
    }
    setSaving(true);
    try {
      const created = await admin.createCode({
        amountPln: amt,
        maxUses: max,
        label: label.trim() || undefined,
      });
      await copyCode(created.code);
      setLastCreated(created.code);
      setAdding(false);
      setAmount('10');
      setMaxUses('100');
      setLabel('');
      reload();
    } catch (err) {
      setError(err?.message || 'Could not create code.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Page
      title="Codes"
      action={
        <button
          type="button"
          className="ad-btn ad-btn--primary"
          onClick={() => {
            setAdding(true);
            setError('');
            setLastCreated(null);
          }}
        >
          <Icon name="plus" size={16} />
          Add new code
        </button>
      }
    >
      {lastCreated && (
        <p className="ad-muted" style={{ marginBottom: 12 }}>
          Copied to clipboard: <strong>{lastCreated}</strong>
        </p>
      )}
      <AdminContentLoader loading={dailyLoading} minHeight="120px">
        <Card title="Discord daily reward" padded>
          <p className="ad-muted" style={{ marginBottom: 16 }}>
            Used when the bot posts the midnight Warsaw code and when an admin runs
            the /daily command. Each user can still redeem only once per day.
          </p>
          <form onSubmit={saveDailySettings}>
            <div className="ad-form-row" style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Field label="Amount (PLN per redeem)">
                <input
                  className="ad-input"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={dailyAmount}
                  onChange={(e) => {
                    setDailyAmount(e.target.value);
                    setDailySaved(false);
                  }}
                  required
                />
              </Field>
              <Field label="Global uses">
                <input
                  className="ad-input"
                  type="number"
                  min="1"
                  step="1"
                  value={dailyMaxUses}
                  onChange={(e) => {
                    setDailyMaxUses(e.target.value);
                    setDailySaved(false);
                  }}
                  required
                />
              </Field>
            </div>
            {dailyError && <p className="ad-login__error">{dailyError}</p>}
            {dailySaved && !dailyError && (
              <p className="ad-muted">Saved — next daily code will use these values.</p>
            )}
            <div style={{ marginTop: 12 }}>
              <button
                type="submit"
                className="ad-btn ad-btn--primary"
                disabled={dailySaving || dailyLoading}
              >
                {dailySaving ? 'Saving…' : 'Save daily settings'}
              </button>
            </div>
          </form>
        </Card>
      </AdminContentLoader>
      <AdminContentLoader loading={loading}>
        <Card>
          <DataTable
            columns={COLUMNS}
            rows={codeRows}
            empty="No codes yet — create the first one with the button above"
            pageSize={10}
          />
        </Card>
      </AdminContentLoader>

      <Modal open={adding} onClose={() => setAdding(false)} title="New code">
        <form onSubmit={submit}>
          <Field label="Amount — credited to user balance">
            <input
              className="ad-input"
              type="number"
              min="0.01"
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </Field>
          <Field label="Max uses">
            <input
              className="ad-input"
              type="number"
              min="1"
              step="1"
              value={maxUses}
              onChange={(e) => setMaxUses(e.target.value)}
              required
            />
          </Field>
          <Field label="Label (optional)">
            <input
              className="ad-input"
              type="text"
              placeholder="e.g. Weekend promo"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
            />
          </Field>
          {error && <p className="ad-login__error">{error}</p>}
          <div className="ad-modal__footer">
            <button
              type="button"
              className="ad-btn ad-btn--ghost"
              onClick={() => setAdding(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ad-btn ad-btn--primary"
              disabled={saving}
            >
              {saving ? 'Creating…' : 'Create and copy code'}
            </button>
          </div>
        </form>
      </Modal>
    </Page>
  );
}
