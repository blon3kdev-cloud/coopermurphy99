import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import './FeaturedBannerPromo.css';

const AUTO_ADVANCE_MS = 5000;

const PROMO_SLIDES = [
  {
    key: 'bets',
    to: '/bets',
    variant: 'media',
    wash: 'blue',
    value: '10.0+',
    valueClass: 'promo-banner__value--blue',
    label: 'Extra odds on parlays in Bets!',
  },
  {
    key: 'rewards',
    to: '/free-rewards',
    variant: 'solid',
    wash: 'gold',
    value: '1,000+',
    valueClass: 'promo-banner__value--gold',
    label: 'Available in free rewards',
  },
  {
    key: 'casino',
    to: '/casino',
    variant: 'solid',
    wash: 'purple',
    value: '6+',
    valueClass: 'promo-banner__value--purple',
    label: 'Original casino games',
  },
];

function PromoSlide({ slide }) {
  const cardClass =
    slide.variant === 'media'
      ? 'promo-banner__card promo-banner__card--media'
      : 'promo-banner__card promo-banner__card--solid';

  return (
    <Link className={cardClass} to={slide.to}>
      {slide.variant === 'media' ? (
        <div className="promo-banner__media" aria-hidden="true">
          <div className="promo-banner__media-scrim" />
        </div>
      ) : null}
      <div
        className={`promo-banner__wash promo-banner__wash--${slide.wash}`}
        aria-hidden="true"
      />
      <div className="promo-banner__body">
        <p className={`promo-banner__value ${slide.valueClass}`}>{slide.value}</p>
        <p className="promo-banner__label">{slide.label}</p>
      </div>
    </Link>
  );
}

function FeaturedBannerPromo() {
  const [activeIndex, setActiveIndex] = useState(0);
  const slideCount = PROMO_SLIDES.length;

  const goTo = useCallback((index) => {
    setActiveIndex(((index % slideCount) + slideCount) % slideCount);
  }, [slideCount]);

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 900px)');
    let id;

    const start = () => {
      if (!mq.matches) return;
      id = window.setInterval(() => {
        setActiveIndex((i) => (i + 1) % slideCount);
      }, AUTO_ADVANCE_MS);
    };

    const stop = () => {
      if (id !== undefined) {
        window.clearInterval(id);
        id = undefined;
      }
    };

    const onChange = () => {
      stop();
      start();
    };

    start();
    mq.addEventListener('change', onChange);
    return () => {
      stop();
      mq.removeEventListener('change', onChange);
    };
  }, [slideCount]);

  return (
    <section className="promo-banner" aria-label="Promotions">
      <div className="promo-banner__inner">
        <div
          className="promo-banner__viewport"
          aria-roledescription="carousel"
        >
          <div
            className="promo-banner__track"
            style={{ transform: `translate3d(-${activeIndex * 100}%, 0, 0)` }}
          >
            {PROMO_SLIDES.map((slide) => (
              <div key={slide.key} className="promo-banner__slide">
                <PromoSlide slide={slide} />
              </div>
            ))}
          </div>
        </div>

        <div
          className="promo-banner__dots"
          role="tablist"
          aria-label="Choose promotion"
        >
          {PROMO_SLIDES.map((slide, i) => (
            <button
              key={slide.key}
              type="button"
              role="tab"
              className="promo-banner__dot"
              aria-selected={i === activeIndex}
              aria-label={`Promotion ${i + 1} of ${slideCount}`}
              onClick={() => goTo(i)}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

export default FeaturedBannerPromo;
