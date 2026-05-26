import { useState, useEffect } from 'react';
import { useAppBootstrap } from '../../context/AppBootstrapContext';
import './PageLoader.css';

export default function PageLoader({ children }) {
  const { ready } = useAppBootstrap();
  const [phase, setPhase] = useState('loading');

  useEffect(() => {
    if (!ready) {
      setPhase('loading');
      return undefined;
    }

    let exitTimer;
    setPhase('exiting');
    exitTimer = window.setTimeout(() => setPhase('done'), 360);

    return () => window.clearTimeout(exitTimer);
  }, [ready]);

  const showLoader = phase !== 'done';
  const showContent = phase === 'done';

  return (
    <>
      <div
        className={`page-loader__shell${showContent ? ' page-loader__shell--visible' : ''}`}
        aria-hidden={!showContent}
      >
        {children}
      </div>
      {showLoader ? (
        <div
          className={`page-loader${phase === 'exiting' ? ' page-loader--exit' : ''}`}
          aria-busy={phase === 'loading'}
          aria-live="polite"
          aria-label="Loading"
        >
          <div className="page-loader__spinner" aria-hidden="true" />
        </div>
      ) : null}
    </>
  );
}
