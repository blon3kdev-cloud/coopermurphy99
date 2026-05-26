import React from 'react';
import LegalDocument from '../components/legal-document/LegalDocument';

function ProvablyFairPage() {
  return (
    <LegalDocument
      title="Provably Fair"
      subtitle="How casino outcomes are generated on czutkabet.com."
      lastUpdated="May 22, 2026"
    >
      <p>
        Dice, Limbo, and Keno each use a random server seed. The result is
        calculated from that seed with fixed math and saved with the round so it
        can be checked later.
      </p>

      <h2>In short</h2>
      <ul>
        <li>Every round stores a unique server seed and the outcome.</li>
        <li>Outcomes are not picked by hand after you bet.</li>
        <li>Payouts follow the rules shown in each game.</li>
      </ul>

      <h2>Limits</h2>
      <p>
        We do not show a seed hash before you bet, and there is no verify button in
        the app yet. Seeds are for post-round checks (e.g. via support), not the
        full commit-before-play model. Sports and crypto products use other rules.
      </p>

      <p>
        Think a round is wrong? Contact us on Discord or Telegram with the time
        and game — we can compare it to the stored seed.
      </p>
    </LegalDocument>
  );
}

export default ProvablyFairPage;
