const GENERIC_LABELS = new Set(['tak', 'nie', 'yes', 'no']);

function isTeamLabel(label) {
  const s = String(label ?? '').trim();
  if (!s) return false;
  return !GENERIC_LABELS.has(s.toLowerCase());
}

function normalizeMatchupTitle(title) {
  return String(title).replace(/\s+vs\.?\s+/gi, ' - ').replace(/\s+/g, ' ').trim();
}

function looksLikeMatchupTitle(title) {
  return /\s[-–—]\s/.test(title) || /\s+vs\.?\s+/i.test(title);
}

/** Card / slip title — prefer API title when it is already a full matchup. */
export function marketDisplayTitle(market) {
  const title = String(market?.title ?? '').trim();
  const yesLabel = String(market?.yesLabel ?? market?.yes_label ?? '').trim();
  const noLabel = String(market?.noLabel ?? market?.no_label ?? '').trim();

  if (title && looksLikeMatchupTitle(title)) {
    return normalizeMatchupTitle(title);
  }

  if (isTeamLabel(yesLabel) && isTeamLabel(noLabel)) {
    return `${yesLabel} - ${noLabel}`;
  }

  if (title && (title === yesLabel || title === noLabel)) {
    if (isTeamLabel(yesLabel) && isTeamLabel(noLabel)) {
      return `${yesLabel} - ${noLabel}`;
    }
  }

  return title || (isTeamLabel(yesLabel) && isTeamLabel(noLabel)
    ? `${yesLabel} - ${noLabel}`
    : yesLabel || noLabel || 'Bet');
}
