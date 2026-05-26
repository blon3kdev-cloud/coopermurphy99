import React from 'react';
import LegalDocument from '../components/legal-document/LegalDocument';

function PrywatnoscPage() {
  return (
    <LegalDocument
      title="Privacy Policy"
      subtitle="How we handle your data when you use the Service."
      lastUpdated="May 24, 2026"
    >
      <p>
        This policy explains how we process personal data when you use our
        entertainment platform (&quot;the Service&quot;). We collect only what is
        needed to run accounts, games, and security.
      </p>

      <h2>What we collect</h2>
      <p>
        We store account and activity data required to operate the Service — for
        example login credentials, linked messenger IDs, balances, game history,
        and basic security logs. We do not ask for email or government ID for a
        standard account.
      </p>

      <h2>Third-party platforms</h2>
      <p>
        Parts of the Service run through Discord and/or Telegram. Those apps
        process your data under their own policies. We receive only what is
        needed to link your account and send service messages.
      </p>

      <h2>Your rights</h2>
      <p>
        Where applicable law grants them, you may request access, correction, or
        deletion of your data. Contact us through the support channels listed on
        the Service.
      </p>

      <h2>Cookies</h2>
      <p>
        We use essential session cookies to keep you logged in. We do not use
        advertising or third-party analytics cookies on the standard Service.
      </p>

      <h2>Changes</h2>
      <p>
        We may update this policy. The date at the top shows the current version.
        Continued use after changes means you have been informed of the update.
      </p>
    </LegalDocument>
  );
}

export default PrywatnoscPage;
