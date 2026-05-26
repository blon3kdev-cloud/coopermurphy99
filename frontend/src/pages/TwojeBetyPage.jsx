import React, { useCallback, useEffect, useRef, useState } from 'react';
import { stripCurrencySuffix } from '../lib/currencyFormat';
import { chipUrl } from '../lib/assets';
import EmptyState from '../components/empty-state/EmptyState';
import PageContentLoader from '../components/page-loader/PageContentLoader';
import {
  BetTicketCluster,
  ShareColumnSpacer,
  formatCombinedMultiplier,
} from '../components/bet-ticket/BetTicket';
import ShareBetModal from '../components/share-bet-sheet/ShareBetModal';
import { userBets } from '../lib/api';
import { getCached } from '../lib/apiCache';
import { useVisibilityInterval } from '../hooks/useVisibilityInterval';
import { useInfiniteScroll } from '../hooks/useInfiniteScroll';
import './TwojeBetyPage.css';

function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden>
      <path
        d="M2 6l3 3 5-5"
        stroke="#1ed760"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function clusterActive(bets) {
  const out = [];
  const used = new Set();
  for (const bet of bets) {
    if (used.has(bet.id)) continue;
    if (bet.slipGroupId) {
      const group = bets
        .filter((b) => b.slipGroupId === bet.slipGroupId)
        .sort((a, b) => a.id - b.id);
      group.forEach((b) => used.add(b.id));
      out.push({ isParlay: group.length > 1, bets: group });
    } else {
      used.add(bet.id);
      out.push({ isParlay: false, bets: [bet] });
    }
  }
  return out;
}

function historyFromCache() {
  const hit = getCached('user:bets:history');
  if (!hit) return { items: null, nextBefore: null };
  if (Array.isArray(hit)) return { items: hit, nextBefore: null };
  return {
    items: Array.isArray(hit.items) ? hit.items : null,
    nextBefore: hit.nextBefore ?? null,
  };
}

export default function TwojeBetyPage() {
  const cachedActive = getCached('user:bets:active');
  const cachedHistory = historyFromCache();
  const [active, setActive] = useState(
    () => (Array.isArray(cachedActive) ? cachedActive : null),
  );
  const [history, setHistory] = useState(cachedHistory.items);
  const [historyNextBefore, setHistoryNextBefore] = useState(cachedHistory.nextBefore);
  const [loading, setLoading] = useState(
    () => !Array.isArray(cachedActive) || cachedHistory.items == null,
  );
  const [historyLoadingMore, setHistoryLoadingMore] = useState(false);
  const [shareBets, setShareBets] = useState(null);
  const historyNextBeforeRef = useRef(historyNextBefore);
  historyNextBeforeRef.current = historyNextBefore;

  const loadActive = useCallback(({ silent = false } = {}) => {
    return userBets
      .getActive()
      .then((a) => setActive(Array.isArray(a) ? a : []))
      .catch(() => setActive([]))
      .finally(() => {
        if (!silent) setLoading(false);
      });
  }, []);

  const loadBets = useCallback(({ silent = false } = {}) => {
    if (!silent) setLoading(true);
    return Promise.all([
      userBets.getActive().then((a) => setActive(Array.isArray(a) ? a : [])),
      userBets.getHistory().then((page) => {
        setHistory(page.items);
        setHistoryNextBefore(page.nextBefore);
      }),
    ])
      .catch(() => {
        setActive([]);
        setHistory([]);
        setHistoryNextBefore(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const loadMoreHistory = useCallback(() => {
    const before = historyNextBeforeRef.current;
    if (!before || historyLoadingMore) return;
    setHistoryLoadingMore(true);
    userBets
      .getHistory({ before })
      .then((page) => {
        setHistory((prev) => [...(prev ?? []), ...page.items]);
        setHistoryNextBefore(page.nextBefore);
      })
      .catch(() => setHistoryNextBefore(null))
      .finally(() => setHistoryLoadingMore(false));
  }, [historyLoadingMore]);

  useEffect(() => {
    const hasCache =
      Array.isArray(cachedActive) && cachedHistory.items != null;
    loadBets({ silent: hasCache });
  }, [loadBets, cachedActive, cachedHistory.items]);

  useVisibilityInterval(() => loadActive({ silent: true }), 10_000, true);

  const hasMoreHistory = Boolean(historyNextBefore);
  const sentinelRef = useInfiniteScroll({
    hasMore: hasMoreHistory,
    loading: historyLoadingMore || loading,
    onLoadMore: loadMoreHistory,
  });

  const isEmpty = !loading && active?.length === 0 && history?.length === 0;
  const activeClusters = !loading && active ? clusterActive(active) : [];

  const openShare = (payload) => {
    const bets = Array.isArray(payload) ? payload : [payload];
    if (bets.length) setShareBets(bets);
  };
  const closeShare = () => setShareBets(null);

  return (
    <PageContentLoader loading={loading} minHeight="min(70vh, 640px)">
      <ShareBetModal
        open={Boolean(shareBets?.length)}
        bets={shareBets}
        bet={shareBets?.[0]}
        totalWin={shareBets?.[shareBets.length - 1]?.potWin}
        onClose={closeShare}
      />
      <div className="yb__page">
        <div className="yb__inner">
          {isEmpty ? (
            <EmptyState
              title="You have no bets yet"
              hint="Place your first bet to see it here."
            />
          ) : !loading ? (
            <>
              {activeClusters.length > 0 && (
                <section className="yb__section">
                  <ShareColumnSpacer />
                  <h2 className="yb__section-heading">Active</h2>

                  {activeClusters.map((cluster) => (
                    <BetTicketCluster
                      key={cluster.bets.map((b) => b.id).join('-')}
                      bets={cluster.bets}
                      isParlay={cluster.isParlay}
                      showFullStats
                      onShare={openShare}
                    />
                  ))}
                </section>
              )}

              {(history ?? []).map((group) => {
                const isSingleHistory = !group.isParlay && group.bets.length === 1;
                const ticketBets = isSingleHistory
                  ? [
                      {
                        ...group.bets[0],
                        cost: group.totalCost ?? group.bets[0].cost,
                        potWin: group.totalWin ?? group.bets[0].potWin,
                      },
                    ]
                  : group.bets;
                const showOutsideTotals =
                  !isSingleHistory && (group.totalCost || group.totalWin);

                return (
                  <section
                    key={`${group.date}-${group.bets.map((b) => b.id).join('-')}`}
                    className="yb__section yb__section--group"
                  >
                    <ShareColumnSpacer />
                    <div className="yb__group-header">
                      <span className="yb__group-date">{group.date}</span>
                      {group.ended && (
                        <span className="yb__group-badge">
                          <CheckIcon />
                          Settled
                        </span>
                      )}
                    </div>

                    <BetTicketCluster
                      bets={ticketBets}
                      isParlay={group.isParlay}
                      showFullStats={isSingleHistory}
                      ended
                      onShare={openShare}
                    />

                    {showOutsideTotals && (
                        <div className="yb__totals-card">
                          {group.isParlay && group.bets.length > 1 && (
                            <div className="yb__stat-row">
                              <span className="yb__stat-label">Multiplier total</span>
                              <span className="yb__stat-value">
                                {formatCombinedMultiplier(group.bets)}
                              </span>
                            </div>
                          )}
                          {group.totalCost && (
                            <div className="yb__stat-row">
                              <span className="yb__stat-label">cost</span>
                              <span className="yb__stat-win-wrap">
                                <span className="yb__stat-value">
                                  {stripCurrencySuffix(group.totalCost)}
                                </span>
                                <img src={chipUrl} alt="" className="yb__stat-chip" />
                              </span>
                            </div>
                          )}
                          {group.totalWin && (
                            <div className="yb__stat-row">
                              <span className="yb__stat-label">Your winnings</span>
                              <span className="yb__stat-win-wrap">
                                <span className="yb__stat-win">
                                  {stripCurrencySuffix(group.totalWin)}
                                </span>
                                <img src={chipUrl} alt="" className="yb__stat-chip" />
                              </span>
                            </div>
                          )}
                        </div>
                    )}
                  </section>
                );
              })}

              {hasMoreHistory && (
                <div
                  ref={sentinelRef}
                  className="feed-scroll-sentinel feed-scroll-sentinel--yb"
                  aria-hidden={!historyLoadingMore}
                >
                  {historyLoadingMore && (
                    <p className="feed-scroll-sentinel__label">Loading more…</p>
                  )}
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </PageContentLoader>
  );
}
