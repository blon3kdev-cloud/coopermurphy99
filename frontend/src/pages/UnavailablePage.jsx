import React, { useEffect } from 'react';
import './NotFoundPage.css';

function UnavailablePage({ title = 'Unavailable — czutkabet' }) {
  useEffect(() => {
    document.title = title;
    return () => {
      document.title = 'czutkabet';
    };
  }, [title]);

  return (
    <section
      className="not-found not-found--standalone"
      aria-labelledby="unavailable-title"
    >
      <div className="not-found__card">
        <h1 id="unavailable-title" className="not-found__code">
          —
        </h1>
        <p className="not-found__message">
          Unavailable currently. The site is temporarily offline — please check
          back later.
        </p>
      </div>
    </section>
  );
}

export default UnavailablePage;
