import React, { useState } from 'react';
import AdminContentLoader from './AdminContentLoader';
import { Page, Card } from './AdminUI';
import { useAdminQuery } from './useAdminQuery';
import { admin } from '../lib/api';

export default function Security() {
  const [busy, setBusy] = useState(false);
  const { loading, data, setData } = useAdminQuery(
    () => admin.getAdminSettings().then((s) => ({ siteUnavailable: Boolean(s?.siteUnavailable) })),
    [],
  );
  const siteUnavailable = Boolean(data?.siteUnavailable);

  const toggle = async () => {
    setBusy(true);
    try {
      const s = await admin.patchAdminSettings({ siteUnavailable: !siteUnavailable });
      setData({ siteUnavailable: Boolean(s?.siteUnavailable) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page title="Security">
      <AdminContentLoader loading={loading} minHeight="200px">
        <Card title="Site availability" padded>
          <div className="ad-setting-row">
            <div className="ad-setting-row__text">
              <strong className="ad-setting-row__label">Maintenance mode</strong>
              <p className="ad-muted">
                When enabled, visitors see an unavailable page. The admin panel
                stays accessible so you can turn the site back on.
              </p>
            </div>
            <label className={`ad-switch${busy ? ' ad-switch--busy' : ''}`}>
              <input
                type="checkbox"
                checked={siteUnavailable}
                disabled={busy}
                onChange={toggle}
                aria-label="Maintenance mode"
              />
              <span className="ad-switch__track" aria-hidden="true" />
            </label>
          </div>
        </Card>
      </AdminContentLoader>
    </Page>
  );
}
