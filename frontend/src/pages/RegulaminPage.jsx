import React from 'react';
import LegalDocument from '../components/legal-document/LegalDocument';

function RegulaminPage() {
  return (
    <LegalDocument
      title="Terms of Service"
      subtitle="Rules for using the Service."
      lastUpdated="May 24, 2026"
    >
      <blockquote>
        The Service is an online entertainment platform with simulated betting
        and casino-style play. Balances are play credits only — not real money,
        legal tender, or a regulated financial product.
      </blockquote>

      <h2>Eligibility</h2>
      <p>
        You must be at least 18 (or the minimum age in your region, if higher).
        You are responsible for ensuring that use of the Service is allowed where
        you live.
      </p>

      <h2>Accounts</h2>
      <p>
        Keep your login details secret. One account per person unless we approve
        otherwise. Activity on your account is treated as yours unless you show
        unauthorized access despite reasonable care.
      </p>

      <h2>Play credits</h2>
      <p>
        Stakes, wins, and losses affect your in-service balance only. We may
        correct errors or abuse. Lost credits through normal play are not
        refundable as cash.
      </p>

      <h2>User transfers</h2>
      <p>
        Some users move credits through flows coordinated on the platform.
        Transfers between users are their own arrangement; we do not act as a
        bank or payment institution and do not guarantee recovery of off-platform
        disputes.
      </p>

      <h2>Prohibited conduct</h2>
      <p>You must not cheat, abuse the platform, attack our systems, harass
        others, use multiple accounts for unfair advantage, or break applicable
        law.</p>

      <h2>Disclaimer</h2>
      <p>
        The Service is provided &quot;as is&quot;. We do not warrant uninterrupted
        or error-free operation. To the extent permitted by law, we are not liable
        for indirect damages or losses from downtime or third-party platforms.
      </p>

      <h2>Changes and termination</h2>
      <p>
        We may update these Terms or suspend accounts that violate them. Continued
        use after changes means you accept the updated Terms. Contact support
        through the channels listed on the Service with questions.
      </p>
    </LegalDocument>
  );
}

export default RegulaminPage;
