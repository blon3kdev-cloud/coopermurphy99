import React, { useMemo, useState } from 'react';
import AdminContentLoader from './AdminContentLoader';
import {
  Page,
  Card,
  DataTable,
  Toolbar,
  Modal,
  Badge,
  DetailList,
  Icon,
  fmt,
} from './AdminUI';
import { useAdminQuery } from './useAdminQuery';
import { admin } from '../lib/api';

const COLUMNS = [
  { key: 'username', label: 'User' },
  { key: 'email', label: 'Email' },
  {
    key: 'platform',
    label: 'Platform',
    render: (r) => {
      const tone =
        r.platform === 'discord' ? 'blue' : r.platform === 'telegram' ? 'purple' : 'gray';
      return <Badge tone={tone}>{r.platform}</Badge>;
    },
  },
  { key: 'balance', label: 'Balance', render: (r) => fmt.money(r.balance) },
  { key: 'deposited', label: 'Deposited', render: (r) => fmt.money(r.deposited) },
  { key: 'wagered', label: 'Wagered', render: (r) => fmt.money(r.wagered) },
  {
    key: 'status',
    label: 'Status',
    render: (r) => (
      <Badge tone={r.status === 'active' ? 'green' : 'red'}>{r.status}</Badge>
    ),
  },
  { key: 'joined', label: 'Joined' },
];

export default function Users() {
  const [search, setSearch] = useState('');
  const [platform, setPlatform] = useState('all');
  const [status, setStatus] = useState('all');
  const [selectedName, setSelectedName] = useState(null);
  const [overrides, setOverrides] = useState({});
  const [oddsOverrides, setOddsOverrides] = useState({});
  const [oddsModalOpen, setOddsModalOpen] = useState(false);
  const [oddsInput, setOddsInput] = useState('');
  const [oddsSaving, setOddsSaving] = useState(false);
  const { loading, data: users, reload } = useAdminQuery(
    () => admin.getUsers().then((data) => (Array.isArray(data) ? data : [])),
    [],
  );
  const userRows = users ?? [];

  const enriched = useMemo(
    () =>
      userRows.map((u) => ({
        ...u,
        status: overrides[u.username] ?? u.status,
        casinoOdds: oddsOverrides[u.username] ?? u.casinoOdds,
        key: u.username,
      })),
    [userRows, overrides, oddsOverrides],
  );

  const rows = useMemo(() => {
    const q = search.trim().toLowerCase();
    return enriched.filter((u) => {
      if (q && !u.username.toLowerCase().includes(q) && !u.email.toLowerCase().includes(q)) {
        return false;
      }
      if (platform !== 'all' && u.platform !== platform) return false;
      if (status !== 'all' && u.status !== status) return false;
      return true;
    });
  }, [enriched, search, platform, status]);

  const selected = selectedName
    ? enriched.find((u) => u.username === selectedName) ?? null
    : null;

  const toggleBan = async () => {
    if (!selected) return;
    const next = selected.status === 'active' ? 'banned' : 'active';
    setOverrides((prev) => ({ ...prev, [selected.username]: next }));
    await admin.setUserStatus(selected.username, next);
  };

  const openOddsModal = () => {
    if (!selected) return;
    setOddsInput(
      selected.casinoOdds != null && Number.isFinite(selected.casinoOdds)
        ? String(selected.casinoOdds)
        : '',
    );
    setOddsModalOpen(true);
  };

  const saveCasinoOdds = async () => {
    if (!selected || oddsSaving) return;
    const raw = oddsInput.trim().replace(',', '.');
    const parsed = raw === '' ? null : Number.parseFloat(raw);
    if (parsed !== null && (!Number.isFinite(parsed) || parsed < 1 || parsed > 99)) {
      window.alert('Enter a value between 1 and 99, or leave empty for the site default.');
      return;
    }
    setOddsSaving(true);
    try {
      const res = await admin.setUserCasinoOdds(selected.username, parsed);
      const nextOdds = res?.casinoOdds ?? null;
      setOddsOverrides((prev) => ({ ...prev, [selected.username]: nextOdds }));
      setOddsModalOpen(false);
      await reload?.();
    } catch (err) {
      window.alert(err?.message || 'Could not save casino odds.');
    } finally {
      setOddsSaving(false);
    }
  };

  const clearCasinoOdds = async () => {
    if (!selected || oddsSaving) return;
    setOddsSaving(true);
    try {
      await admin.setUserCasinoOdds(selected.username, null);
      setOddsOverrides((prev) => ({ ...prev, [selected.username]: null }));
      setOddsInput('');
      setOddsModalOpen(false);
      await reload?.();
    } catch (err) {
      window.alert(err?.message || 'Could not reset casino odds.');
    } finally {
      setOddsSaving(false);
    }
  };

  return (
    <Page title="Users">
      <AdminContentLoader loading={loading}>
      <Card>
        <Toolbar>
          <input
            className="ad-input ad-input--grow"
            placeholder="Search username or platform ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="ad-select"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
          >
            <option value="all">All platforms</option>
            <option value="discord">Discord</option>
            <option value="telegram">Telegram</option>
            <option value="both">Both</option>
          </select>
          <select
            className="ad-select"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
          >
            <option value="all">All statuses</option>
            <option value="active">Active</option>
            <option value="banned">Banned</option>
          </select>
        </Toolbar>
        <DataTable
          columns={COLUMNS}
          rows={rows}
          onRowClick={(r) => setSelectedName(r.username)}
          empty="No users match your filters"
          pageSize={8}
        />
      </Card>
      </AdminContentLoader>

      <Modal
        open={!!selected}
        onClose={() => {
          setSelectedName(null);
          setOddsModalOpen(false);
        }}
        title={selected ? `@${selected.username}` : ''}
      >
        {selected && (
          <>
            <DetailList
              items={[
                ['Platform ID', selected.email],
                ['Platform', selected.platform],
                ['Status', selected.status],
                ['Balance', fmt.money(selected.balance)],
                ['Total deposited', fmt.money(selected.deposited)],
                ['Total wagered', fmt.money(selected.wagered)],
                ['Total bets placed', selected.totalBets],
                ['Lifetime profit', fmt.money(selected.lifetimeProfit)],
                ['Joined', selected.joined],
                ['Last active', selected.lastActive],
                ['IP address', selected.ip],
                [
                  'Casino odds',
                  selected.casinoOdds != null
                    ? `${selected.casinoOdds}% (custom)`
                    : 'Default',
                ],
              ]}
            />
            <div className="ad-modal__footer">
              <button
                type="button"
                className="ad-btn ad-btn--primary"
                onClick={openOddsModal}
              >
                <Icon name="trendingUp" size={16} />
                Adjust odds
              </button>
              {selected.status === 'banned' ? (
                <button
                  type="button"
                  className="ad-btn ad-btn--success"
                  onClick={toggleBan}
                >
                  <Icon name="check" size={16} />
                  Unban user
                </button>
              ) : (
                <button
                  type="button"
                  className="ad-btn ad-btn--danger"
                  onClick={toggleBan}
                >
                  <Icon name="x" size={16} />
                  Ban user
                </button>
              )}
            </div>
          </>
        )}
      </Modal>

      <Modal
        open={oddsModalOpen && !!selected}
        onClose={() => !oddsSaving && setOddsModalOpen(false)}
        title={selected ? `Casino odds — @${selected.username}` : ''}
      >
        {selected && (
          <>
            <p className="ad-field-hint">
              Optional casino odds for this user (1–99%). Higher = better outcomes. Leave
              empty for the site default.
            </p>
            <label className="ad-field">
              <span className="ad-field__label">Odds %</span>
              <input
                className="ad-input"
                type="text"
                inputMode="decimal"
                placeholder="e.g. 95"
                value={oddsInput}
                onChange={(e) => setOddsInput(e.target.value)}
                disabled={oddsSaving}
              />
            </label>
            <div className="ad-modal__footer">
              <button
                type="button"
                className="ad-btn ad-btn--ghost"
                onClick={clearCasinoOdds}
                disabled={oddsSaving}
              >
                Use default
              </button>
              <button
                type="button"
                className="ad-btn ad-btn--primary"
                onClick={saveCasinoOdds}
                disabled={oddsSaving}
              >
                Save
              </button>
            </div>
          </>
        )}
      </Modal>
    </Page>
  );
}
