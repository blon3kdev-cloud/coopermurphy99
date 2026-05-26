import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import './NotFoundPage.css';

function NotFoundPage({ title = 'Page not found — czutkabet' }) {
  useEffect(() => {
    document.title = title;
    return () => {
      document.title = 'czutkabet';
    };
  }, [title]);

  return (
    <section className="not-found" aria-labelledby="not-found-title">
      <div className="not-found__card">
        <h1 id="not-found-title" className="not-found__code">
          404
        </h1>
        <p className="not-found__message">
          This page does not exist or was moved. Check the address or head back
          home.
        </p>
        <Link to="/" className="not-found__home-btn">
          Go to home
        </Link>
      </div>
    </section>
  );
}

export default NotFoundPage;
