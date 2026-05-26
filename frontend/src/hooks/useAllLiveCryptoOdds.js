import { useEffect, useMemo, useRef, useState } from 'react';
import { pickCryptoOdds } from '../lib/cryptoOdds';
import {
  refreshBtcSnapshot,
  roundBtcUsd,
  subscribeBtcFairOdds,
  subscribeBtcPrice,
  subscribeBtcWindows,
} from '../lib/btcLivePrice';
import { remainingSecForWindow, windowRolledOver } from '../lib/cryptoWindowClock';

const WINDOWS = ['5m', '30m', '24h'];

/**
 * Live Higher/Lower odds for all BTC windows in one subscription (one 1s timer).
 * @returns {Record<string, { up: number|null, down: number|null, price: *, remaining: number }>}
 */
export function useAllLiveCryptoOdds() {
  const [price, setPrice] = useState(null);
  const [windows, setWindows] = useState(null);
  const [fairOdds, setFairOdds] = useState(null);
  const [tick, setTick] = useState(0);
  const lastRolledSig = useRef(null);

  useEffect(
    () =>
      subscribeBtcPrice((p) => {
        setPrice((prev) => {
          const next = roundBtcUsd(p);
          return next === prev ? prev : next;
        });
      }),
    [],
  );

  useEffect(() => subscribeBtcWindows(setWindows), []);
  useEffect(() => subscribeBtcFairOdds(setFairOdds), []);

  useEffect(() => {
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!windows) return;
    const rolledKey = WINDOWS.find(
      (key) => windows[key]?.windowEnd != null && windowRolledOver(key, windows[key].windowEnd),
    );
    if (!rolledKey) {
      lastRolledSig.current = null;
      return;
    }
    const sig = `${rolledKey}:${windows[rolledKey].windowEnd}`;
    if (lastRolledSig.current === sig) return;
    lastRolledSig.current = sig;
    refreshBtcSnapshot();
  }, [windows]);

  return useMemo(() => {
    const out = {};
    for (const key of WINDOWS) {
      const win = windows?.[key];
      let remaining = 0;
      if (win?.windowEnd != null) {
        remaining = remainingSecForWindow(key, win.windowEnd);
      } else {
        remaining = Math.max(0, Math.floor(win?.remainingSec ?? 0));
      }
      const open = win?.openPrice;
      const meta = { ...(fairOdds || {}), ...(win?.oddsContext || {}) };
      const picked = pickCryptoOdds(key, win?.odds, meta, price, open, remaining);
      out[key] = { up: picked.up, down: picked.down, price, remaining };
    }
    void tick;
    return out;
  }, [windows, price, fairOdds, tick]);
}
