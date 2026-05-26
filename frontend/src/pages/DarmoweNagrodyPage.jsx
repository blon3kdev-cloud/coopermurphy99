import React, { useState } from 'react';
import FaqSection, { FAQ_ITEMS_NAGRODY } from '../components/faq-section/FaqSection';
import PageContentLoader from '../components/page-loader/PageContentLoader';
import FreeRewardsContent from '../components/free-rewards/FreeRewardsContent';
import './DarmoweNagrodyPage.css';

function DarmoweNagrodyPage() {
  const [loading, setLoading] = useState(true);

  return (
    <PageContentLoader loading={loading} minHeight="min(70vh, 640px)">
      <div className="dn__page">
        <div className="dn__inner">
          <FreeRewardsContent onLoadingChange={setLoading} />
          <FaqSection items={FAQ_ITEMS_NAGRODY} />
        </div>
      </div>
    </PageContentLoader>
  );
}

export default DarmoweNagrodyPage;
