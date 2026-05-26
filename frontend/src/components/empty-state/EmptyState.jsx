import React from 'react';
import './EmptyState.css';

/**
 * Subtle, neutral empty-state block. Use it anywhere a list/grid might come
 * back without rows so the layout never feels broken.
 *
 * @param {{
 *   title: string;
 *   hint?: string;
 *   action?: React.ReactNode;
 *   className?: string;
 *   compact?: boolean;
 * }} props
 */
export default function EmptyState({ title, hint, action, className = '', compact = false }) {
  return (
    <div
      className={[
        'empty-state',
        compact && 'empty-state--compact',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      role="status"
    >
      <p className="empty-state__title">{title}</p>
      {hint && <p className="empty-state__hint">{hint}</p>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}
