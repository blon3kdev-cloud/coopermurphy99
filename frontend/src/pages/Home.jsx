import React, { useDeferredValue, useState } from 'react';
import FeaturedBannerPromo from '../components/featured-banner-promo/FeaturedBannerPromo';
import MarketSearch from '../components/market-search/MarketSearch';
import FeaturedBets from '../components/featured-bets/FeaturedBets';
import FeaturedKasyno from '../components/featured-kasyno/FeaturedKasyno';
import FeaturedKrypto from '../components/featured-krypto/FeaturedKrypto';
import FaqSection from '../components/faq-section/FaqSection';

function Home() {
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);

  return (
    <>
      <FeaturedBannerPromo />
      <MarketSearch query={query} onQueryChange={setQuery} />
      <FeaturedBets query={deferredQuery} />
      <FeaturedKasyno query={deferredQuery} />
      <FeaturedKrypto query={deferredQuery} />
      <FaqSection />
    </>
  );
}

export default Home;
