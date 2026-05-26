import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AdminContentLoader from './AdminContentLoader';
import {
  Page,
  Card,
  DataTable,
  Field,
  Icon,
  Badge,
  Modal,
  StatTile,
  fmt,
} from './AdminUI';
import { admin } from '../lib/api';
import { safeImageUrl, safePreviewImageUrl } from '../lib/safeUrl';

const sideLabelFor = (placement, marketById) => {
  const m = marketById[placement.market];
  if (!m) return placement.side;
  return placement.side === 'yes' ? m.yesLabel : m.noLabel;
};

const SideBadge = ({ placement, marketById }) => (
  <Badge tone={placement.side === 'yes' ? 'green' : 'orange'}>
    {sideLabelFor(placement, marketById)}
  </Badge>
);

/** Admin list rows use yes/no; public markets API uses yesOdds/noOdds strings. */
function normalizeAdminMarket(raw) {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return null;
  if (Object.prototype.hasOwnProperty.call(raw, 'created')) return null;
  const yes = Number(raw.yes);
  const no = Number(raw.no);
  if (!Number.isFinite(yes) || !Number.isFinite(no)) return null;
  return {
    ...raw,
    yes,
    no,
    yesLabel: raw.yesLabel ?? 'Yes',
    noLabel: raw.noLabel ?? 'No',
    status: raw.status ?? 'active',
    bets: raw.bets ?? 0,
    volume: raw.volume ?? 0,
  };
}

function marketOddsPair(row) {
  const yes = Number(row?.yes);
  const no = Number(row?.no);
  return {
    yes: Number.isFinite(yes) ? yes : null,
    no: Number.isFinite(no) ? no : null,
  };
}

function formatMarketOdds(row) {
  const { yes, no } = marketOddsPair(row);
  if (yes == null || no == null) return '—';
  return `${row.yesLabel ?? 'Yes'} ${yes.toFixed(2)} / ${row.noLabel ?? 'No'} ${no.toFixed(2)}`;
}

const MARKET_COLUMNS_BASE = [
  {
    key: 'image',
    label: '',
    width: 64,
    render: (r) => {
      const src = safeImageUrl(r.image);
      return src ? (
        <img src={src} alt="" className="ad-thumb" />
      ) : (
        <span className="ad-thumb ad-thumb--empty" aria-hidden="true" />
      );
    },
  },
  { key: 'title', label: 'Title' },
  { key: 'eventDate', label: 'Match date', render: (r) => r.eventDate || '—' },
  {
    key: 'odds',
    label: 'Odds',
    render: (r) => formatMarketOdds(r),
  },
  { key: 'bets', label: 'Bets placed', render: (r) => fmt.number(r.bets) },
  { key: 'volume', label: 'Volume', render: (r) => fmt.money(r.volume) },
  {
    key: 'status',
    label: 'Status',
    render: (r) => {
      const tone =
        r.status === 'active' ? 'green' : r.status === 'cancelled' ? 'orange' : 'gray';
      return <Badge tone={tone}>{r.status}</Badge>;
    },
  },
];

const placementColumns = (marketById) => [
  { key: 'user', label: 'User' },
  {
    key: 'market',
    label: 'Market',
    render: (r) => marketById[r.market]?.title ?? r.market,
  },
  { key: 'side', label: 'Side', render: (r) => <SideBadge placement={r} marketById={marketById} /> },
  { key: 'stake', label: 'Stake', render: (r) => fmt.money(r.stake) },
  { key: 'odds', label: 'Odds', render: (r) => r.odds.toFixed(2) },
  {
    key: 'potential',
    label: 'Potential win',
    render: (r) => fmt.money(r.stake * r.odds),
  },
  { key: 'date', label: 'Date' },
];

const marketPlacementColumns = (marketById) => [
  { key: 'user', label: 'User' },
  { key: 'side', label: 'Side', render: (r) => <SideBadge placement={r} marketById={marketById} /> },
  { key: 'stake', label: 'Stake', render: (r) => fmt.money(r.stake) },
  { key: 'odds', label: 'Odds', render: (r) => r.odds.toFixed(2) },
  {
    key: 'potential',
    label: 'Potential win',
    render: (r) => fmt.money(r.stake * r.odds),
  },
  { key: 'date', label: 'Date' },
];

const OUTCOME = {
  yes: { tone: 'green', label: (b) => `${b.yesLabel} won` },
  no: { tone: 'orange', label: (b) => `${b.noLabel} won` },
  draw: { tone: 'gray', label: () => 'Draw · all lost' },
  cashback: { tone: 'purple', label: () => 'Push · refunded' },
};

function isportsErrorMessage(err) {
  const detail = err?.body?.detail;
  if (detail === 'isports_api_not_configured') {
    return 'Set I_SPORTS_API_KEY in the backend.';
  }
  if (detail === 'isports_api_error') {
    return 'iSports API error — try again.';
  }
  if (detail === 'no_matches') {
    return 'No upcoming matches (NBA or top football leagues).';
  }
  if (detail === 'sport_not_supported') {
    return 'This sport is not supported.';
  }
  if (detail === 'session_expired') {
    return 'Session expired — start again.';
  }
  if (detail?.error === 'nothing_created') {
    return `Nothing created. Skipped: ${(detail.skipped || []).join('; ')}`;
  }
  return err?.message || 'Operation failed.';
}

function parseAdminEventDate(s) {
  if (!s || typeof s !== 'string') return null;
  const m = s.trim().match(/^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2}):(\d{2})$/);
  if (!m) return null;
  return new Date(Date.UTC(+m[3], +m[2] - 1, +m[1], +m[4], +m[5]));
}

function marketEndedByDate(market) {
  const d = parseAdminEventDate(market.eventDate);
  if (!d) return false;
  return d.getTime() <= Date.now();
}

const RESOLVE_PHASE_LABELS = {
  precheck: 'Sprawdzanie aktywnych zakładów po terminie meczu…',
  schedule: 'Pobieranie terminarza i wyników z iSports…',
  live: 'Sprawdzanie statystyk na żywo…',
  players: 'Pobieranie bramek strzelców…',
  settle: 'Rozstrzyganie rynków i wypłaty…',
};

function AutoResolveModal({ open, onClose, onDone, bets }) {
  const [phase, setPhase] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [statusLine, setStatusLine] = useState('');
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const runStartedRef = useRef(false);
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  const reset = () => {
    setPhase('idle');
    setProgress(0);
    setStatusLine('');
    setPreview(null);
    setResult(null);
    setError('');
    runStartedRef.current = false;
  };

  useEffect(() => {
    if (!open) {
      reset();
      return undefined;
    }

    let cancelled = false;
    let tick = null;
    let phaseTimer = null;

    const clearTimers = () => {
      if (tick) clearInterval(tick);
      if (phaseTimer) clearInterval(phaseTimer);
      tick = null;
      phaseTimer = null;
    };

    const run = async () => {
      setPhase('precheck');
      setProgress(8);
      setStatusLine(RESOLVE_PHASE_LABELS.precheck);
      setError('');
      setResult(null);

      const localEnded = (Array.isArray(bets) ? bets : []).filter(
        (b) =>
          b.status === 'active'
          && b.autoResolve
          && b.source === 'isports'
          && marketEndedByDate(b),
      );

      try {
        const prev = await admin.previewIsportsAutoResolve();
        if (cancelled) return;
        setPreview(prev);
        const endedCount = Number(prev?.endedCount ?? localEnded.length);

        if (endedCount < 1) {
          setPhase('skipped');
          setProgress(100);
          setStatusLine('');
          return;
        }

        setPhase('running');
        setProgress(18);
        setStatusLine(RESOLVE_PHASE_LABELS.schedule);

        tick = setInterval(() => {
          setProgress((p) => {
            if (p >= 92) return p;
            return p + 1.5;
          });
        }, 350);

        const phases = [
          [28, 'schedule'],
          [48, 'live'],
          [62, 'players'],
          [78, 'settle'],
        ];
        let phaseIdx = 0;
        phaseTimer = setInterval(() => {
          if (phaseIdx < phases.length) {
            const [pct, key] = phases[phaseIdx];
            setProgress((p) => Math.max(p, pct));
            setStatusLine(RESOLVE_PHASE_LABELS[key]);
            phaseIdx += 1;
          }
        }, 1200);

        const data = await admin.runIsportsAutoResolve();
        if (cancelled) return;
        clearTimers();
        setResult(data);
        setPhase('done');
        setProgress(100);
        setStatusLine('Zakończono.');
        onDoneRef.current?.();
      } catch (err) {
        clearTimers();
        if (cancelled) return;
        setError(isportsErrorMessage(err));
        setPhase('error');
        setProgress(100);
      }
    };

    if (!runStartedRef.current) {
      runStartedRef.current = true;
      run();
    }

    return () => {
      cancelled = true;
      clearTimers();
    };
  }, [open, bets]);

  const resolved = Number(result?.resolved ?? 0);
  const checked = Number(result?.checked ?? preview?.endedCount ?? 0);
  const logs = Array.isArray(result?.logs) ? result.logs : [];

  const handleClose = () => {
    if (phase === 'precheck' || phase === 'running') return;
    onClose();
  };

  const footer = (
    <div className="ad-modal__footer">
      <button
        type="button"
        className="ad-btn ad-btn--primary"
        onClick={handleClose}
        disabled={phase === 'precheck' || phase === 'running'}
      >
        {phase === 'done' || phase === 'skipped' || phase === 'error' ? 'Zamknij' : 'Anuluj'}
      </button>
    </div>
  );

  return (
    <Modal open={open} onClose={handleClose} title="Automatyczne rozstrzyganie" wide>
      {(phase === 'precheck' || phase === 'running') && (
        <>
          <p className="ad-field-hint" style={{ margin: 0 }}>{statusLine}</p>
          <div className="ad-progress" role="progressbar" aria-valuenow={Math.round(progress)} aria-valuemin={0} aria-valuemax={100}>
            <div className="ad-progress__bar" style={{ width: `${progress}%` }} />
          </div>
        </>
      )}

      {phase === 'skipped' && (
        <p className="ad-field-hint" style={{ margin: 0 }}>
          Brak aktywnych zakładów iSports po terminie meczu — nie ma czego sprawdzać w API.
          {Number(preview?.upcomingCount ?? 0) > 0
            ? ` (${preview.upcomingCount} ${preview.upcomingCount === 1 ? 'mecz' : 'mecze'} jeszcze w przyszłości.)`
            : ''}
        </p>
      )}

      {phase === 'done' && (
        <>
          <p style={{ margin: '0 0 12px' }}>
            Sprawdzono <strong>{checked}</strong> {checked === 1 ? 'rynek' : 'rynki'}, rozstrzygnięto{' '}
            <strong>{resolved}</strong>.
          </p>
          {logs.length > 0 ? (
            <ul className="ad-resolve-log">
              {logs.map((entry) => (
                <li
                  key={`${entry.marketId}-${entry.message}`}
                  className={`ad-resolve-log__item ad-resolve-log__item--${entry.level || 'info'}`}
                >
                  <strong>{entry.title || entry.marketId}</strong>
                  <br />
                  <span className="ad-muted">{entry.message}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="ad-field-hint" style={{ margin: 0 }}>
              Żaden mecz nie ma jeszcze statusu „zakończony” w iSports — spróbuj ponownie później.
            </p>
          )}
        </>
      )}

      {phase === 'error' && (
        <p className="ad-field-hint" style={{ color: 'var(--ad-danger, #e55)', margin: 0 }}>{error}</p>
      )}

      {footer}
    </Modal>
  );
}

function AutoAddBetsModal({ open, onClose, onCreated }) {
  const [step, setStep] = useState('sport');
  const [sessionSport, setSessionSport] = useState('');
  const [amount, setAmount] = useState('5');
  const [sessionId, setSessionId] = useState('');
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [match, setMatch] = useState(null);
  const [variants, setVariants] = useState([]);
  const [selected, setSelected] = useState({});
  const [loading, setLoading] = useState(false);
  const [loadingPhase, setLoadingPhase] = useState('');
  const [loadProgress, setLoadProgress] = useState(0);
  const [loadStatusLine, setLoadStatusLine] = useState('');
  const [loadedMatchCount, setLoadedMatchCount] = useState(0);
  const [oddsBookmaker, setOddsBookmaker] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [playerPanel, setPlayerPanel] = useState(null);
  const pageCacheRef = useRef({});

  const reset = () => {
    setStep('sport');
    setSessionSport('');
    setAmount('5');
    setSessionId('');
    setPage(0);
    setTotal(0);
    setMatch(null);
    setVariants([]);
    setSelected({});
    setLoading(false);
    setLoadingPhase('');
    setLoadProgress(0);
    setLoadStatusLine('');
    setLoadedMatchCount(0);
    setOddsBookmaker('');
    setError('');
    setSuccess('');
    setPlayerPanel(null);
    pageCacheRef.current = {};
  };

  const snapshotPage = (pageIndex) => ({
    page: pageIndex,
    total,
    match,
    variants,
    selected,
    success,
  });

  const applySnapshot = (snap) => {
    setPage(snap.page);
    setTotal(snap.total);
    setMatch(snap.match);
    setVariants(snap.variants);
    setSelected(snap.selected);
    setSuccess(snap.success || '');
  };

  useEffect(() => {
    if (!open) {
      reset();
      return undefined;
    }
    return undefined;
  }, [open]);

  const cachePageFromResponse = (pageIndex, data) => {
    const vars = Array.isArray(data.variants) ? data.variants : [];
    const main = vars.find((v) => v.isMain);
    const snap = {
      page: data.page ?? pageIndex,
      total: data.total ?? 0,
      match: data.match ?? null,
      variants: vars,
      selected: main ? { [main.key]: true } : {},
      success: '',
    };
    pageCacheRef.current[pageIndex] = snap;
    return snap;
  };

  const loadPage = async (sid, pageIndex, { apply = true } = {}) => {
    const cached = pageCacheRef.current[pageIndex];
    if (cached) {
      if (apply) applySnapshot(cached);
      return cached;
    }
    const data = await admin.getIsportsSessionPage(sid, { page: pageIndex, perPage: 1 });
    const snap = cachePageFromResponse(pageIndex, data);
    if (apply) applySnapshot(snap);
    return snap;
  };

  const preloadAllPages = async (sid, matchTotal, sportKey) => {
    const totalMatches = Math.max(0, Number(matchTotal) || 0);
    if (totalMatches < 1) return;
    for (let i = 0; i < totalMatches; i += 1) {
      setLoadStatusLine(
        sportKey === 'basketball'
          ? `Loading NBA odds — match ${i + 1} of ${totalMatches}…`
          : `Loading odds and scorers — match ${i + 1} of ${totalMatches}…`,
      );
      await loadPage(sid, i, { apply: false });
      const done = i + 1;
      setLoadedMatchCount(done);
      setLoadProgress(Math.round((done / totalMatches) * 100));
    }
    applySnapshot(pageCacheRef.current[0]);
  };

  const startIsportsSession = async (sport) => {
    const n = parseInt(amount, 10);
    if (!Number.isFinite(n) || n < 1 || n > 20) {
      setError('Enter a number of matches from 1 to 20.');
      return;
    }
    setSessionSport(sport);
    setLoading(true);
    setLoadingPhase('schedule');
    setLoadProgress(0);
    setLoadStatusLine('Fetching schedule (iSports: max 1 request / 60 s per day; first load may take a few minutes)…');
    setLoadedMatchCount(0);
    setError('');
    setSuccess('');
    pageCacheRef.current = {};
    try {
      const data = await admin.createIsportsSession({ sport, amount: n });
      const sid = data.sessionId;
      const matchTotal = data.total ?? 0;
      setSessionSport(data.sport || sport);
      setSessionId(sid);
      setOddsBookmaker(data.oddsBookmaker || '');
      setTotal(matchTotal);
      if (matchTotal < 1) {
        setError('No matches found for this sport.');
        setStep('sport');
        return;
      }
      setStep('loading');
      setLoadingPhase('odds');
      setLoadProgress(0);
      await preloadAllPages(sid, matchTotal, data.sport || sport);
      setLoadProgress(100);
      setLoadedMatchCount(matchTotal);
      setStep('wizard');
    } catch (err) {
      setError(isportsErrorMessage(err));
      setStep('sport');
    } finally {
      setLoading(false);
      setLoadingPhase('');
      setLoadStatusLine('');
    }
  };

  const toggleVariant = (key) => {
    setSelected((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const selectedKeys = useMemo(
    () => Object.keys(selected).filter((k) => selected[k]),
    [selected],
  );

  const createSelected = async () => {
    if (!sessionId || !match?.matchId || selectedKeys.length === 0) {
      setError('Select at least one bet type.');
      return;
    }
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      const res = await admin.createIsportsMarkets(sessionId, {
        matchId: match.matchId,
        variants: selectedKeys,
      });
      const n = res.count ?? (res.created?.length ?? 0);
      const msg = `Created ${n} bet(s).`;
      setSuccess(msg);
      pageCacheRef.current[page] = { ...snapshotPage(page), success: msg };
      await onCreated?.();
      if (res.skipped?.length) {
        setError(`Skipped: ${res.skipped.join('; ')}`);
      }
    } catch (err) {
      setError(isportsErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const goPage = async (nextPage) => {
    if (!sessionId || loading || nextPage < 0 || nextPage >= total || nextPage === page) return;

    setPlayerPanel(null);
    pageCacheRef.current[page] = snapshotPage(page);

    if (pageCacheRef.current[nextPage]) {
      applySnapshot(pageCacheRef.current[nextPage]);
      setError('');
      return;
    }

    setLoading(true);
    setLoadingPhase('odds');
    setError('');
    try {
      await loadPage(sessionId, nextPage);
    } catch (err) {
      setError(isportsErrorMessage(err));
    } finally {
      setLoading(false);
      setLoadingPhase('');
    }
  };

  const sportTiles = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <Field label="Number of matches">
        <input
          className="ad-input"
          type="number"
          min={1}
          max={20}
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          disabled={loading}
        />
      </Field>
      <p className="ad-field-hint" style={{ margin: 0 }}>
        Football: big-five, UEFA cups, or major internationals — any teams in those leagues (women&apos;s and U teams skipped). Basketball: NBA only, winner market.
      </p>
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <button
          type="button"
          className="ad-btn ad-btn--primary"
          disabled={loading}
          onClick={() => startIsportsSession('football')}
        >
          Football
        </button>
        <button
          type="button"
          className="ad-btn ad-btn--primary"
          disabled={loading}
          onClick={() => startIsportsSession('basketball')}
        >
          NBA
        </button>
      </div>
      {loading && loadingPhase === 'schedule' && (
        <p className="ad-field-hint">{loadStatusLine}</p>
      )}
    </div>
  );

  const loadingPanel = (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <p className="ad-field-hint" style={{ margin: 0 }}>
        {loadStatusLine || (loadingPhase === 'schedule'
          ? 'Fetching schedule…'
          : 'Loading all matches…')}
      </p>
      <div
        className="ad-progress"
        role="progressbar"
        aria-valuenow={Math.round(loadProgress)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Loading matches"
      >
        <div className="ad-progress__bar" style={{ width: `${loadProgress}%` }} />
      </div>
      {total > 0 && loadingPhase === 'odds' && (
        <p className="ad-field-hint" style={{ margin: 0 }}>
          {loadedMatchCount} / {total} {total === 1 ? 'match' : 'matches'} ready
        </p>
      )}
    </div>
  );

  const isBasketball = sessionSport === 'basketball';
  const mainVariant = variants.find((v) => v.isMain);
  const playerVariants = isBasketball ? [] : variants.filter((v) => v.category === 'player_scorer');
  const homeScorers = playerVariants.filter((v) => v.teamSide === 'home');
  const awayScorers = playerVariants.filter((v) => v.teamSide === 'away');

  const openPlayerPanel = (v) => {
    if (!v?.isTopPlayer) return;
    setPlayerPanel(v);
  };

  const renderVariantRow = (v) => {
    const topPlayer = !!v.isTopPlayer;
    return (
      <li key={v.key}>
        <label
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: 10,
            cursor: loading ? 'default' : 'pointer',
          }}
        >
          <input
            type="checkbox"
            checked={!!selected[v.key]}
            disabled={loading}
            onChange={() => toggleVariant(v.key)}
          />
          <span style={{ flex: 1, minWidth: 0 }}>
            <span style={{ display: 'block', fontWeight: 500 }}>{v.label}</span>
            <span className="ad-field-hint">
              {v.yesLabel} {Number(v.yesOdds).toFixed(2)} / {v.noLabel} {Number(v.noOdds).toFixed(2)}
              {v.seasonGoals != null ? ` · ${v.seasonGoals} season goals` : ''}
              {v.oddsSource ? ` · ${v.oddsSource}` : ''}
            </span>
            {topPlayer ? (
              <button
                type="button"
                className="ad-btn ad-btn--ghost"
                style={{ marginTop: 6, padding: '4px 10px', fontSize: 12 }}
                disabled={loading}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  openPlayerPanel(v);
                }}
              >
                Player profile
              </button>
            ) : null}
          </span>
        </label>
      </li>
    );
  };

  const playerSidebar = playerPanel?.topPlayer ? (
    <aside
      className="ad-isports-player-panel"
      aria-label="Player profile"
    >
      <div className="ad-isports-player-panel__head">
        <p className="ad-isports-player-panel__title">
          {playerPanel.topPlayer.displayName || playerPanel.playerName}
        </p>
        <button
          type="button"
          className="ad-btn ad-btn--ghost ad-btn--icon"
          aria-label="Close"
          onClick={() => setPlayerPanel(null)}
        >
          <Icon name="x" size={18} />
        </button>
      </div>
      <dl className="ad-isports-player-panel__meta">
        <div>
          <dt>Club</dt>
          <dd>{playerPanel.topPlayer.team || playerPanel.teamName || '—'}</dd>
        </div>
        <div>
          <dt>League</dt>
          <dd>{playerPanel.topPlayer.league || '—'}</dd>
        </div>
        <div>
          <dt>Season goals</dt>
          <dd>{playerPanel.seasonGoals ?? '—'}</dd>
        </div>
        <div>
          <dt>Match</dt>
          <dd>
            {match?.homeName} vs {match?.awayName}
          </dd>
        </div>
      </dl>
      <p className="ad-field-hint" style={{ margin: 0 }}>
        This player is on the top European scorers list — you can add a “scores a goal” bet.
      </p>
      <button
        type="button"
        className="ad-btn ad-btn--primary"
        style={{ marginTop: 12, width: '100%' }}
        disabled={loading}
        onClick={() => {
          setSelected((prev) => ({ ...prev, [playerPanel.key]: true }));
          setPlayerPanel(null);
        }}
      >
        Select bet
      </button>
    </aside>
  ) : null;

  const wizard = match && (
    <div
      className={playerPanel ? 'ad-isports-wizard ad-isports-wizard--with-player' : 'ad-isports-wizard'}
      style={{ display: 'flex', flexDirection: 'column', gap: 14 }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
        <span className="ad-field-hint" style={{ margin: 0 }}>
          Match {page + 1} / {total}
        </span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            type="button"
            className="ad-btn ad-btn--ghost"
            disabled={loading || page <= 0}
            onClick={() => goPage(page - 1)}
          >
            Previous
          </button>
          <button
            type="button"
            className="ad-btn ad-btn--ghost"
            disabled={loading || page >= total - 1}
            onClick={() => goPage(page + 1)}
          >
            Next
          </button>
        </div>
      </div>
      <div
        style={{
          padding: 12,
          borderRadius: 8,
          border: '1px solid var(--ad-border, rgba(255,255,255,0.08))',
          background: 'var(--ad-surface-2, rgba(255,255,255,0.03))',
        }}
      >
        <p style={{ margin: '0 0 4px', fontWeight: 600 }}>
          {match.homeName} vs {match.awayName}
        </p>
        <p className="ad-field-hint" style={{ margin: 0 }}>
          {[match.leagueName || match.leagueShortName, match.eventDate].filter(Boolean).join(' · ')}
        </p>
        {oddsBookmaker ? (
          <p className="ad-field-hint" style={{ margin: '8px 0 0' }}>
            {isBasketball ? 'ML odds' : '1X2 odds'}: {mainVariant?.oddsSource || oddsBookmaker}
          </p>
        ) : null}
      </div>
      {variants.length === 0 ? (
        <p className="ad-field-hint">No odds available for this match.</p>
      ) : (
        <>
          <Field label="Main market — match winner">
            {mainVariant ? (
              <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                {renderVariantRow(mainVariant)}
              </ul>
            ) : (
              <p className="ad-field-hint">
                {isBasketball ? 'No winner odds for this match.' : 'No 1X2 odds for this match.'}
              </p>
            )}
          </Field>
          {!isBasketball && (
          <Field label="Scorers — top 3 per team (profile for listed top players)">
            {playerVariants.length > 0 ? (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: 12,
                }}
              >
                <div>
                  <p className="ad-field-hint" style={{ margin: '0 0 8px', fontWeight: 600 }}>
                    {match.homeName}
                  </p>
                  <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {homeScorers.map(renderVariantRow)}
                  </ul>
                </div>
                <div>
                  <p className="ad-field-hint" style={{ margin: '0 0 8px', fontWeight: 600 }}>
                    {match.awayName}
                  </p>
                  <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {awayScorers.map(renderVariantRow)}
                  </ul>
                </div>
              </div>
            ) : (
              <p className="ad-field-hint" style={{ margin: 0 }}>
                No league scorer list for this league (requires iSports Stats plan).
              </p>
            )}
          </Field>
          )}
        </>
      )}
      {success && (
        <p className="ad-field-hint" style={{ color: 'var(--ad-success, #5c8)' }}>{success}</p>
      )}
      {playerSidebar}
    </div>
  );

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Auto-add bets"
      wide={step === 'wizard' || step === 'sport' || step === 'loading'}
    >
      <div className="ad-form">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {step === 'sport' && sportTiles}
          {step === 'loading' && loadingPanel}
          {step === 'wizard' && wizard}
          {error && (
            <p className="ad-field-hint" style={{ color: 'var(--ad-danger, #e55)' }}>{error}</p>
          )}
        </div>
        <div className="ad-modal__footer">
          <button type="button" className="ad-btn ad-btn--ghost" onClick={onClose} disabled={loading || step === 'loading'}>
            Close
          </button>
          {step === 'wizard' && (
            <button
              type="button"
              className="ad-btn ad-btn--primary"
              disabled={loading || selectedKeys.length === 0}
              onClick={createSelected}
            >
              {loading ? 'Creating…' : 'Create selected'}
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}

function EditMarketModal({ market, onClose, onSaved }) {
  const [form, setForm] = useState({
    title: market?.title ?? '',
    yesLabel: market?.yesLabel ?? 'Yes',
    noLabel: market?.noLabel ?? 'No',
    yes: market?.yes?.toString() ?? '',
    no: market?.no?.toString() ?? '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!market) return;
    setForm({
      title: market.title ?? '',
      yesLabel: market.yesLabel ?? 'Yes',
      noLabel: market.noLabel ?? 'No',
      yes: market.yes?.toString() ?? '',
      no: market.no?.toString() ?? '',
    });
    setError('');
  }, [market]);

  if (!market) return null;

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await admin.updateBet(market.id, {
        title: form.title,
        yesLabel: form.yesLabel,
        noLabel: form.noLabel,
        yes: parseFloat(form.yes),
        no: parseFloat(form.no),
      });
      onSaved();
      onClose();
    } catch (err) {
      setError(err?.message || 'Could not save.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open onClose={onClose} title="Edit market" wide>
      <form className="ad-form" onSubmit={submit}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Field label="Title">
            <input className="ad-input" value={form.title} onChange={update('title')} required />
          </Field>
          <div className="ad-row-2">
            <Field label="Yes / home label">
              <input className="ad-input" value={form.yesLabel} onChange={update('yesLabel')} />
            </Field>
            <Field label="No / away label">
              <input className="ad-input" value={form.noLabel} onChange={update('noLabel')} />
            </Field>
          </div>
          <div className="ad-row-2">
            <Field label="Yes odds">
              <input className="ad-input" type="number" step="0.01" value={form.yes} onChange={update('yes')} required />
            </Field>
            <Field label="No odds">
              <input className="ad-input" type="number" step="0.01" value={form.no} onChange={update('no')} required />
            </Field>
          </div>
          {error && <p className="ad-field-hint" style={{ color: 'var(--ad-danger, #e55)' }}>{error}</p>}
        </div>
        <div className="ad-modal__footer">
          <button type="button" className="ad-btn ad-btn--ghost" onClick={onClose} disabled={loading}>Cancel</button>
          <button type="submit" className="ad-btn ad-btn--primary" disabled={loading}>Save</button>
        </div>
      </form>
    </Modal>
  );
}

export function Bets() {
  const [resolving, setResolving] = useState(null);
  const [resolved, setResolved] = useState({});
  const [viewingMarket, setViewingMarket] = useState(null);
  const [editingMarket, setEditingMarket] = useState(null);
  const [autoAddOpen, setAutoAddOpen] = useState(false);
  const [autoResolveOpen, setAutoResolveOpen] = useState(false);
  const [bets, setBets] = useState([]);
  const [placements, setPlacements] = useState([]);
  const [loading, setLoading] = useState(true);

  const applyBetsPayload = (b, p) => {
    const markets = (Array.isArray(b) ? b : [])
      .map(normalizeAdminMarket)
      .filter(Boolean);
    setBets(markets);
    setPlacements(Array.isArray(p) ? p : []);
    setResolved(
      Object.fromEntries(
        markets
          .filter((m) => m.status === 'resolved' && m.outcome)
          .map((m) => [m.id, m.outcome]),
      ),
    );
  };

  const loadBets = useCallback(async (opts = {}) => {
    const { silent = false } = opts;
    if (!silent) setLoading(true);
    try {
      const [b, p] = await Promise.all([admin.getBets(), admin.getBetPlacements()]);
      applyBetsPayload(b, p);
    } catch {
      applyBetsPayload([], []);
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBets();
  }, [loadBets]);

  const onAutoCreated = () => loadBets({ silent: true });

  const marketById = useMemo(
    () => Object.fromEntries(bets.map((b) => [b.id, b])),
    [bets],
  );

  const stats = useMemo(() => {
    const totalVolume = placements.reduce((sum, p) => sum + p.stake, 0);
    return {
      activeMarkets: bets.filter((b) => b.status === 'active').length,
      betsPlaced: placements.length,
      volume: totalVolume,
      avgStake: placements.length > 0 ? totalVolume / placements.length : 0,
    };
  }, [bets, placements]);

  const placementsForViewing = useMemo(() => {
    if (!viewingMarket) return [];
    return placements.filter((p) => p.market === viewingMarket.id);
  }, [viewingMarket, placements]);

  const settle = async (outcome) => {
    setResolved((r) => ({ ...r, [resolving.id]: outcome }));
    await admin.resolveBet(resolving.id, outcome);
    setResolving(null);
  };

  const removeMarket = async (market) => {
    const pendingOnMarket = placements.filter(
      (p) => p.market === market.id,
    ).length;
    const msg = pendingOnMarket > 0
      ? `Delete "${market.title}"? ${pendingOnMarket} open user bets will be refunded (cashback).`
      : `Delete "${market.title}"?`;
    if (!window.confirm(msg)) return;
    await admin.deleteBet(market.id);
    loadBets({ silent: true });
  };

  const marketColumns = [
    ...MARKET_COLUMNS_BASE,
    {
      key: 'actions',
      label: '',
      width: 220,
      render: (r) => {
        if (r.status === 'cancelled') {
          return <span className="ad-muted">Deleted</span>;
        }
        const out = resolved[r.id];
        return (
          <div className="ad-actions-row">
            <button
              type="button"
              className="ad-btn ad-btn--ghost ad-btn--sm"
              onClick={() => setEditingMarket(r)}
            >
              Edit
            </button>
            {r.status === 'active' && !out && (
              <button
                type="button"
                className="ad-btn ad-btn--ghost ad-btn--sm"
                onClick={() => setResolving(r)}
              >
                Settle
              </button>
            )}
            {out && (
              <Badge tone={OUTCOME[out].tone}>{OUTCOME[out].label(r)}</Badge>
            )}
            <button
              type="button"
              className="ad-btn ad-btn--ghost ad-btn--sm ad-btn--danger"
              onClick={() => removeMarket(r)}
            >
              Delete
            </button>
          </div>
        );
      },
    },
  ];

  return (
    <Page
      title="Bets"
      action={
        <>
          <button
            type="button"
            className="ad-btn ad-btn--ghost"
            onClick={() => setAutoResolveOpen(true)}
          >
            Automatyczne roztrzyganie
          </button>
          <button
            type="button"
            className="ad-btn ad-btn--ghost"
            onClick={() => setAutoAddOpen(true)}
          >
            Auto-add bets
          </button>
          <Link to="/admin/bets/new" className="ad-btn ad-btn--primary">
            <Icon name="plus" size={16} />
            New bet
          </Link>
        </>
      }
    >
      <AdminContentLoader loading={loading}>
      <div className="ad-stats-grid">
        <StatTile
          value={fmt.number(stats.activeMarkets)}
          label="Active markets"
          icon="target"
          tone="cyan"
        />
        <StatTile
          value={fmt.number(stats.betsPlaced)}
          label="Bets placed"
          icon="users"
          tone="green"
        />
        <StatTile
          value={fmt.money(stats.volume)}
          label="Volume wagered"
          icon="coins"
          tone="orange"
        />
        <StatTile
          value={fmt.money(stats.avgStake)}
          label="Avg stake"
          icon="trendingUp"
          tone="blue"
        />
      </div>

      <Card title="Markets">
        <DataTable
          columns={marketColumns}
          rows={bets}
          empty="No bet markets yet — create one with New bet"
          pageSize={8}
        />
      </Card>

      <Card title="Latest bets placed">
        <DataTable
          columns={placementColumns(marketById)}
          rows={placements}
          empty="No bets have been placed yet"
          pageSize={8}
          onRowClick={(r) => setViewingMarket(marketById[r.market])}
        />
      </Card>
      </AdminContentLoader>

      <AutoAddBetsModal
        open={autoAddOpen}
        onClose={() => setAutoAddOpen(false)}
        onCreated={onAutoCreated}
      />

      <AutoResolveModal
        open={autoResolveOpen}
        onClose={() => setAutoResolveOpen(false)}
        onDone={() => loadBets({ silent: true })}
        bets={bets}
      />

      <EditMarketModal
        market={editingMarket}
        onClose={() => setEditingMarket(null)}
        onSaved={() => loadBets({ silent: true })}
      />

      <Modal
        open={!!resolving}
        onClose={() => setResolving(null)}
        title="Settle bet"
      >
        {resolving && <ResolveOptions bet={resolving} onSelect={settle} />}
      </Modal>

      <Modal
        open={!!viewingMarket}
        onClose={() => setViewingMarket(null)}
        title={viewingMarket?.title ?? ''}
        wide
      >
        {viewingMarket && (
          <>
            <div className="ad-market-meta">
              <Badge tone="green">
                {viewingMarket.yesLabel}{' '}
                {marketOddsPair(viewingMarket).yes?.toFixed(2) ?? '—'}
              </Badge>
              <Badge tone="orange">
                {viewingMarket.noLabel}{' '}
                {marketOddsPair(viewingMarket).no?.toFixed(2) ?? '—'}
              </Badge>
              <span className="ad-market-meta__sep">·</span>
              <span>
                <strong>{placementsForViewing.length}</strong> bets ·{' '}
                <strong>
                  {fmt.money(
                    placementsForViewing.reduce((s, p) => s + p.stake, 0),
                  )}
                </strong>{' '}
                volume
              </span>
            </div>
            <div className="ad-market-placements">
              <DataTable
                columns={marketPlacementColumns(marketById)}
                rows={placementsForViewing}
                empty="No bets placed on this market yet"
              />
            </div>
          </>
        )}
      </Modal>
    </Page>
  );
}

function ResolveOptions({ bet, onSelect }) {
  const { yes, no } = marketOddsPair(bet);
  const opts = [
    {
      key: 'yes',
      tone: 'yes',
      icon: 'check',
      title: `${bet.yesLabel} wins`,
      sub: `Pays ${yes?.toFixed(2) ?? '—'}× to ${bet.yesLabel} stakes`,
    },
    {
      key: 'no',
      tone: 'no',
      icon: 'check',
      title: `${bet.noLabel} wins`,
      sub: `Pays ${no?.toFixed(2) ?? '—'}× to ${bet.noLabel} stakes`,
    },
    {
      key: 'draw',
      tone: 'draw',
      icon: 'x',
      title: 'Draw',
      sub: 'Neither side wins — all stakes lost, no payout',
    },
    {
      key: 'cashback',
      tone: 'push',
      icon: 'refund',
      title: 'Cashback (push)',
      sub: 'Match not played — refund all stakes at 1.00×',
    },
  ];

  return (
    <div className="ad-resolve">
      <p className="ad-resolve__lead">{bet.title}</p>
      {opts.map((o) => (
        <button
          key={o.key}
          type="button"
          className={`ad-resolve__opt ad-resolve__opt--${o.tone}`}
          onClick={() => onSelect(o.key)}
        >
          <span className="ad-resolve__opt-icon">
            <Icon name={o.icon} size={20} />
          </span>
          <span className="ad-resolve__opt-text">
            <span className="ad-resolve__opt-title">{o.title}</span>
            <span className="ad-resolve__opt-sub">{o.sub}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

export function AddBet() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: '',
    image: '',
    yesLabel: 'Yes',
    noLabel: 'No',
    yes: '',
    no: '',
  });

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    await admin.createBet(form);
    navigate('/admin/bets');
  };

  return (
    <Page
      title="New bet"
      action={
        <Link to="/admin/bets" className="ad-btn ad-btn--ghost">
          <Icon name="arrowLeft" size={16} />
          Back
        </Link>
      }
    >
      <form className="ad-form" onSubmit={submit}>
        <Card title="Details" padded>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Field label="Title">
              <input
                className="ad-input"
                placeholder="e.g., Will Bitcoin reach $200k by end of 2026?"
                value={form.title}
                onChange={update('title')}
                required
              />
            </Field>
            <Field label="Image URL">
              <input
                className="ad-input"
                placeholder="https://..."
                value={form.image}
                onChange={update('image')}
              />
              {safePreviewImageUrl(form.image) && (
                <img src={safePreviewImageUrl(form.image)} alt="" className="ad-form__preview" />
              )}
            </Field>
          </div>
        </Card>

        <Card title="Outcomes & odds" padded>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div className="ad-row-2">
              <Field label="Yes / option 1 (e.g. team or Yes)">
                <input
                  className="ad-input"
                  value={form.yesLabel}
                  onChange={update('yesLabel')}
                />
              </Field>
              <Field label="Yes odds">
                <input
                  className="ad-input"
                  type="number"
                  step="0.01"
                  placeholder="1.45"
                  value={form.yes}
                  onChange={update('yes')}
                  required
                />
              </Field>
            </div>
            <div className="ad-row-2">
              <Field label="No / option 2 (e.g. team or No)">
                <input
                  className="ad-input"
                  value={form.noLabel}
                  onChange={update('noLabel')}
                />
              </Field>
              <Field label="No odds">
                <input
                  className="ad-input"
                  type="number"
                  step="0.01"
                  placeholder="2.85"
                  value={form.no}
                  onChange={update('no')}
                  required
                />
              </Field>
            </div>
          </div>
        </Card>

        <div className="ad-form__actions">
          <Link to="/admin/bets" className="ad-btn ad-btn--ghost">
            Cancel
          </Link>
          <button type="submit" className="ad-btn ad-btn--primary">
            Create bet
          </button>
        </div>
      </form>
    </Page>
  );
}
