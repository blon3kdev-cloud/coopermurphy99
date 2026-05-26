import './PageLoader.css';

/**
 * In-page loader overlay (same spinner as initial boot) while section data loads.
 * @param {{ loading: boolean; children: import('react').ReactNode; className?: string; minHeight?: string }} props
 */
export default function PageContentLoader({
  loading,
  children,
  className = '',
  minHeight = 'min(60vh, 520px)',
}) {
  return (
    <div
      className={`page-content-loader ${className}`.trim()}
      style={{ minHeight }}
      aria-busy={loading}
    >
      {children}
      {loading ? (
        <div className="page-content-loader__overlay" aria-live="polite" aria-label="Loading">
          <div className="page-loader__spinner" aria-hidden="true" />
        </div>
      ) : null}
    </div>
  );
}
