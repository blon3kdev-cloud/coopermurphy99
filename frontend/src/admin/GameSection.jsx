import React from 'react';
import AdminContentLoader from './AdminContentLoader';
import {
  Page,
  Card,
  DataTable,
  StatTile,
  DetailList,
  LiveIndicator,
  fmt,
} from './AdminUI';
import { useAdminQuery } from './useAdminQuery';
import { admin } from '../lib/api';

const EMPTY_TOTALS = { plays: 0, rtp: 0, wagered: 0, profit: 0 };

const META = {
  krypto: { title: 'Crypto', icon: 'bitcoin', txPrefix: 'kt', fetch: admin.getKrypto },
  kasyno: { title: 'Casino', icon: 'dice', txPrefix: 'gt', fetch: admin.getKasyno, hasRtp: true },
};

const RTP_COLUMN = { key: 'rtp', label: 'Avg RTP', render: (r) => fmt.percent(r.rtp) };

function gameColumns(variant) {
  const cols = [
    { key: 'name', label: 'Game mode' },
    { key: 'plays', label: 'Plays', render: (r) => fmt.number(r.plays) },
  ];
  if (META[variant]?.hasRtp) cols.push(RTP_COLUMN);
  cols.push(
    { key: 'wagered', label: 'Wagered', render: (r) => fmt.money(r.wagered) },
    { key: 'profit', label: 'Casino profit', render: (r) => fmt.money(r.profit) },
  );
  return cols;
}

const TX_COLUMNS = [
  { key: 'id', label: 'ID' },
  { key: 'user', label: 'User' },
  { key: 'game', label: 'Game' },
  { key: 'bet', label: 'Bet', render: (r) => fmt.money(r.bet) },
  {
    key: 'win',
    label: 'Win',
    render: (r) => (
      <span style={{ color: r.win > 0 ? 'var(--ad-green)' : 'var(--ad-text-muted)' }}>
        {fmt.money(r.win)}
      </span>
    ),
  },
  { key: 'date', label: 'Date' },
];

export default function GameSection({ variant }) {
  const { title, icon, txPrefix, fetch: fetchSection } = META[variant];
  const { loading, data } = useAdminQuery(
    () => fetchSection().then((d) => d ?? { games: [], transactions: [], totals: EMPTY_TOTALS }),
    [variant],
  );

  const games = data?.games ?? [];
  const totals = data?.totals ?? EMPTY_TOTALS;

  const liveTx = data?.transactions ?? [];

  const popular = games.length > 0 ? [...games].sort((a, b) => b.plays - a.plays)[0] : null;

  return (
    <Page title={title}>
      <AdminContentLoader loading={loading}>
      <div className="ad-stats-grid">
        <StatTile value={fmt.number(totals.plays)} label="Total plays" icon={icon} tone="cyan" />
        {META[variant]?.hasRtp && (
          <StatTile value={fmt.percent(totals.rtp)} label="Avg RTP" icon="percent" tone="green" />
        )}
        <StatTile value={fmt.money(totals.wagered)} label="Wagered" icon="coins" tone="orange" />
        <StatTile value={fmt.money(totals.profit)} label="Casino profit" icon="trendingUp" tone="blue" />
      </div>

      <div className="ad-grid-2">
        <Card title="Game modes">
          <DataTable
            columns={gameColumns(variant)}
            rows={games.map((g) => ({ ...g, id: g.name }))}
            empty="No game modes yet"
          />
        </Card>
        <Card title="Most popular">
          {popular ? (
            <div className="ad-popular">
              <div className="ad-popular__head">
                <div className="ad-popular__name">{popular.name}</div>
                <div className="ad-popular__sub">{fmt.number(popular.plays)} plays</div>
              </div>
              <DetailList
                items={[
                  ...(META[variant]?.hasRtp ? [['Avg RTP', fmt.percent(popular.rtp)]] : []),
                  ['Wagered', fmt.money(popular.wagered)],
                  ['Casino profit', fmt.money(popular.profit)],
                ]}
              />
            </div>
          ) : (
            <div className="ad-popular">
              <div className="ad-popular__sub">No data yet</div>
            </div>
          )}
        </Card>
      </div>

      <Card title="Latest transactions" action={<LiveIndicator />}>
        <DataTable columns={TX_COLUMNS} rows={liveTx} empty="No transactions yet" />
      </Card>
      </AdminContentLoader>
    </Page>
  );
}
