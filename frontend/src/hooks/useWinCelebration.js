import { useCallback, useEffect, useRef, useState } from 'react';
import { userBets } from '../lib/api';
import { useVisibilityInterval } from './useVisibilityInterval';

/**
 * Fetches the latest uncelebrated win and opens the win modal once per win (server-tracked).
 */
export function useWinCelebration(enabled) {
  const [celebration, setCelebration] = useState(null);
  const [open, setOpen] = useState(false);
  const modalOpenRef = useRef(false);

  const check = useCallback(() => {
    if (!enabled || modalOpenRef.current) return;
    userBets
      .getPendingCelebration()
      .then((data) => {
        if (!data?.celebrationKey || modalOpenRef.current) return;
        setCelebration(data);
        setOpen(true);
        modalOpenRef.current = true;
      })
      .catch(() => {});
  }, [enabled]);

  useEffect(() => {
    if (enabled) check();
    else {
      setOpen(false);
      setCelebration(null);
      modalOpenRef.current = false;
    }
  }, [enabled, check]);

  useVisibilityInterval(check, 15_000, enabled && !open);

  const close = useCallback(() => {
    const key = celebration?.celebrationKey;
    setOpen(false);
    modalOpenRef.current = false;
    setCelebration(null);
    if (key) {
      userBets.dismissCelebration(key).then(() => check()).catch(() => {});
    }
  }, [celebration, check]);

  return { open, close, celebration };
}
