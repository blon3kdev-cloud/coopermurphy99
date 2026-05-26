import React from 'react';
import { Link } from 'react-router-dom';
import './LegalDocument.css';

function LegalDocument({ title, subtitle, lastUpdated, children }) {
  return (
    <div className="legal-doc">
      <article className="legal-doc__sheet">
        <header className="legal-doc__top">
          <h1 className="legal-doc__title">{title}</h1>
          <div className="legal-doc__top-meta">
            <Link to="/" className="legal-doc__back">
              Back to home
            </Link>
            {lastUpdated ? (
              <span className="legal-doc__updated">Last updated · {lastUpdated}</span>
            ) : null}
          </div>
        </header>
        {subtitle ? (
          <p className="legal-doc__subtitle">{subtitle}</p>
        ) : null}
        <div className="legal-doc__content">{children}</div>
      </article>
    </div>
  );
}

export default LegalDocument;
