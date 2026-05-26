import { useCallback, useRef, useState } from 'react';

const PERSPECTIVE_PX = 1400;
const MAX_DEG = 3;

function motionReduced() {
  return (
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

const neutralTransform = () =>
  `perspective(${PERSPECTIVE_PX}px) rotateX(0deg) rotateY(0deg)`;

/** Pointer-follow 3D tilt; spread onto card root: <article {...useCursorTilt()} /> */
export function useCursorTilt() {
  const ref = useRef(null);
  const [transform, setTransform] = useState(() => neutralTransform());

  const onMouseMove = useCallback((e) => {
    if (motionReduced()) return;
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return;
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    const rotateY = x * 2 * MAX_DEG;
    const rotateX = -y * 2 * MAX_DEG;
    setTransform(
      `perspective(${PERSPECTIVE_PX}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`
    );
  }, []);

  const onMouseLeave = useCallback(() => {
    setTransform(neutralTransform());
  }, []);

  return {
    ref,
    style: { transform },
    onMouseMove,
    onMouseLeave,
  };
}
