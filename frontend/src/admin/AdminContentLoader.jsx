import PageContentLoader from '../components/page-loader/PageContentLoader';

/**
 * In-page loader for admin sections (reuses app spinner, admin-themed overlay).
 */
export default function AdminContentLoader({
  loading,
  children,
  className = '',
  minHeight = 'min(52vh, 480px)',
}) {
  return (
    <PageContentLoader
      loading={loading}
      className={`admin-content-loader ${className}`.trim()}
      minHeight={minHeight}
    >
      {children}
    </PageContentLoader>
  );
}
