import React from 'react';
import './FaqSection.css';

/** @typedef {{ question: string; answer: string }} FaqItem */

/** Default questions — home page */
export const FAQ_ITEMS_HOME = [
  {
    question: 'What is czutkabet.com?',
    answer:
      'czutkabet.com is an online platform for sports-style markets, casino games, and crypto price rounds — all in one place with a single balance.',
  },
  {
    question: 'How Bets work',
    answer:
      'Pick an open market, choose Yes or No, and add it to your slip. Set a stake and place the bet — odds are shown on each card and combined in a parlay when you add more picks.',
  },
  {
    question: 'How Casino Works',
    answer:
      'Open Casino from the menu, pick a game (Dice, Limbo, Keno, and more), and play with your balance. Each round uses fixed rules and provably fair random outcomes.',
  },
  {
    question: 'How Crypto Works',
    answer:
      'Crypto markets let you bet on whether a coin moves Up or Down over a short window. Live odds update until the round closes; add picks to your slip the same way as sports bets.',
  },
];

/** Questions on rewards and referrals */
export const FAQ_ITEMS_NAGRODY = [
  {
    question: 'How do I claim free rewards?',
    answer:
      'Complete visible tasks and VIP progress — Claim buttons or timers on bonuses appear when a reward is ready or a tier is reached.',
  },
  {
    question: 'How do referrals work?',
    answer:
      'Share your personal referral link. New accounts registered through your link earn progress and rewards per the program rules described in the Referrals section on this page.',
  },
  {
    question: 'What is VIP progress?',
    answer:
      'Progress shows movement between tiers (e.g. Silver → Gold). Higher tiers can unlock more bonuses and withdrawal terms from the rewards program.',
  },
];

/**
 * @param {{ items?: FaqItem[]; className?: string }} props
 */
function FaqSection({ items = FAQ_ITEMS_HOME, className = '' }) {
  return (
    <section
      className={`faq ${className}`.trim()}
      aria-label="Questions and answers"
    >
      <div className="faq__inner">
        <div className="faq__list">
          {items.map(({ question, answer }, index) => (
            <details
              key={question}
              className="faq__item"
              {...(index === 0 ? { open: true } : {})}
            >
              <summary className="faq__summary">{question}</summary>
              <p className="faq__answer">{answer}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

export default FaqSection;
