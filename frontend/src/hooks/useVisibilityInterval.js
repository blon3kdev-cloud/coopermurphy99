import { useEffect, useRef } from 'react';

/**
 * Runs `fn` on an interval only while the document tab is visible.
 * Pauses when hidden to save battery and API load (important on iOS).
 *
 * @param {() => void} fn
 * @param {number} ms
 * @param {boolean} [enabled=true]
 */
export function useVisibilityInterval(fn, ms, enabled = true) {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!enabled || ms <= 0) return undefined;

    let id = 0;

    const tick = () => fnRef.current();
    const start = () => {
      window.clearInterval(id);
      id = window.setInterval(tick, ms);
    };
    const stop = () => {
      window.clearInterval(id);
      id = 0;
    };

    const onVis = () => {
      if (document.visibilityState === 'visible') {
        tick();
        start();
      } else {
        stop();
      }
    };

    if (document.visibilityState === 'visible') {
      start();
    }

    document.addEventListener('visibilitychange', onVis);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [ms, enabled]);
}
