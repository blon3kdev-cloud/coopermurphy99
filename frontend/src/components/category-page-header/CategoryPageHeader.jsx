import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ReactComponent as ChevronLeftSvg } from '../../assets/chevron-left.svg';
import './CategoryPageHeader.css';

function CategoryPageHeader({
  title,
  className = '',
  onBack,
  backTo = '/',
  backLabel = 'Back to home',
}) {
  const navigate = useNavigate();
  const handleBack = onBack ?? (() => navigate(backTo));

  return (
    <header className={['category-page-header', className].filter(Boolean).join(' ')} aria-label={title}>
      <div className="category-page-header__inner">
        <button
          type="button"
          className="category-page-header__back"
          onClick={handleBack}
          aria-label={backLabel}
        >
          <span className="category-page-header__back-inner" aria-hidden="true">
            <ChevronLeftSvg className="category-page-header__back-icon" />
          </span>
        </button>
        <h1 className="category-page-header__title">{title}</h1>
      </div>
    </header>
  );
}

export default CategoryPageHeader;
