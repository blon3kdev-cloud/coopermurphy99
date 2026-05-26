import React, { useState } from 'react';
import AdminContentLoader from './AdminContentLoader';
import { Page, StatTile, Segmented, fmt } from './AdminUI';
import { useAdminQuery } from './useAdminQuery';
import { admin } from '../lib/api';

const RANGES = [
  { value: 'today', label: 'Today' },
  { value: '7d', label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
];

const STATS = [
  { key: 'newUsers', label: 'New users', icon: 'users', tone: 'cyan', format: fmt.number },
  { key: 'activeUsers', label: 'Active users', icon: 'users', tone: 'green', format: fmt.number },
  { key: 'deposited', label: 'Money deposited', icon: 'arrowDown', tone: 'purple', format: fmt.money },
  { key: 'wagered', label: 'Money wagered', icon: 'coins', tone: 'orange', format: fmt.money },
  { key: 'profit', label: 'Casino profit', icon: 'trendingUp', tone: 'blue', format: fmt.money },
  { key: 'rtp', label: 'Avg RTP', icon: 'percent', tone: 'red', format: fmt.percent },
];

const EMPTY = { newUsers: 0, activeUsers: 0, deposited: 0, wagered: 0, profit: 0, rtp: 0 };

export default function Overview() {
  const [range, setRange] = useState('today');
  const { loading, data } = useAdminQuery(
    () => admin.getStats(range).then((d) => d ?? EMPTY),
    [range],
  );
  const view = data ?? EMPTY;

  return (
    <Page
      title="Overview"
      action={<Segmented value={range} onChange={setRange} options={RANGES} />}
    >
      <AdminContentLoader loading={loading} minHeight="280px">
        <div className="ad-stats-grid">
          {STATS.map((s) => (
            <StatTile
              key={s.key}
              value={s.format(view[s.key])}
              label={s.label}
              icon={s.icon}
              tone={s.tone}
            />
          ))}
        </div>
      </AdminContentLoader>
    </Page>
  );
}
