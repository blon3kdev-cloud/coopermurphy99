import React, { useState } from 'react';
import './AgeGateModal.css';
import {
  exitSiteAfterAgeDenial,
  hasAgeVerified,
  setAgeVerified,
} from '../../lib/consentCookies';

function AgeGateModal() {
  const [verified, setVerified] = useState(() => hasAgeVerified());

  if (verified) return null;

  const onYes = () => {
    setAgeVerified();
    setVerified(true);
  };

  const onNo = () => {
    exitSiteAfterAgeDenial();
  };

  return (
    <div className="age-gate__backdrop" role="presentation">
      <div
        className="age-gate"
        role="dialog"
        aria-modal="true"
        aria-labelledby="age-gate-title"
      >
        <h2 id="age-gate-title" className="age-gate__title">
          Are you 18 or older?
        </h2>
        <p className="age-gate__text">
          You must be at least 18 years old to use this site. This is an entertainment
          simulation — not a licensed casino.
        </p>
        <div className="age-gate__actions">
          <button type="button" className="age-gate__btn age-gate__btn--yes" onClick={onYes}>
            Yes, I am 18+
          </button>
          <button type="button" className="age-gate__btn age-gate__btn--no" onClick={onNo}>
            No
          </button>
        </div>
      </div>
    </div>
  );
}

export default AgeGateModal;
