import { apiCall } from './client'

export async function fetchCrashState() {
  const data = await apiCall('/games/crash/state')
  return {
    phase: data.phase,
    roundId: data.roundId,
    multiplier: data.multiplier,
    countdown: data.countdown,
    waitingEndsAt: data.waitingEndsAt,
    elapsed: data.elapsed,
    history: data.history ?? [],
    myBet: data.myBet ?? null,
    queuedBet: data.queuedBet ?? null,
    balance: data.balance,
    crashPoint: data.crashPoint,
  }
}

/** @param {{ betAmount: number; autoCashout?: number | null }} payload */
export async function crashBet(payload) {
  const body = { stakePln: payload.betAmount }
  if (payload.autoCashout != null) body.autoCashout = payload.autoCashout
  const data = await apiCall('/games/crash/bet', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return {
    phase: data.phase,
    roundId: data.roundId,
    multiplier: data.multiplier,
    countdown: data.countdown,
    waitingEndsAt: data.waitingEndsAt,
    elapsed: data.elapsed,
    history: data.history ?? [],
    myBet: data.myBet ?? null,
    queuedBet: data.queuedBet ?? null,
    balance: data.balance,
  }
}

export async function crashCashout() {
  const data = await apiCall('/games/crash/cashout', { method: 'POST', body: '{}' })
  return {
    phase: data.phase,
    roundId: data.roundId,
    multiplier: data.multiplier,
    countdown: data.countdown,
    waitingEndsAt: data.waitingEndsAt,
    elapsed: data.elapsed,
    history: data.history ?? [],
    myBet: data.myBet ?? null,
    queuedBet: data.queuedBet ?? null,
    payout: data.payout ?? 0,
    cashoutAt: data.cashoutAt,
    balance: data.balance,
  }
}

export async function crashCancelBet() {
  const data = await apiCall('/games/crash/cancel', { method: 'POST', body: '{}' })
  return {
    phase: data.phase,
    roundId: data.roundId,
    multiplier: data.multiplier,
    countdown: data.countdown,
    waitingEndsAt: data.waitingEndsAt,
    elapsed: data.elapsed,
    history: data.history ?? [],
    myBet: data.myBet ?? null,
    queuedBet: data.queuedBet ?? null,
    balance: data.balance,
  }
}

function mapDice2Session(data) {
  const out = {
    resumed: Boolean(data.resumed),
    sessionId: data.sessionId ?? null,
    difficulty: data.difficulty ?? 'medium',
    tiles: data.tiles ?? [],
    pathPos: data.pathPos ?? 0,
    combinedMult: data.combinedMult ?? 1,
    hasRolled: Boolean(data.hasRolled),
    projectedPayout: data.projectedPayout ?? null,
  }
  if (data.balance != null) {
    out.balances = { PLN: data.balance }
  }
  return out
}

/** @param {{ betAmount: number; difficulty?: 'easy' | 'medium' | 'hard' }} payload */
export async function startDice2(payload) {
  const data = await apiCall('/games/dice2/start', {
    method: 'POST',
    body: JSON.stringify({
      stakePln: payload.betAmount,
      difficulty: payload.difficulty ?? 'medium',
    }),
  })
  return mapDice2Session(data)
}

export async function rollDice2() {
  const data = await apiCall('/games/dice2/roll', { method: 'POST', body: '{}' })
  const out = {
    dieA: data.dieA,
    dieB: data.dieB,
    pathPos: data.pathPos,
    combinedMult: data.combinedMult,
    busted: Boolean(data.busted),
    tileMult: data.tileMult ?? null,
    hasRolled: Boolean(data.hasRolled),
    payout: data.payout ?? null,
    projectedPayout: data.projectedPayout ?? null,
  }
  if (data.balance != null) {
    out.balances = { PLN: data.balance }
  }
  return out
}

export async function cashoutDice2() {
  const data = await apiCall('/games/dice2/cashout', { method: 'POST', body: '{}' })
  return {
    combinedMult: data.combinedMult,
    payout: data.payout,
    balances: { PLN: data.balance },
  }
}

/** @param {{ betAmount: number; overValue: number }} payload */
export async function playDice(payload) {
  const data = await apiCall('/games/dice', {
    method: 'POST',
    body: JSON.stringify({ stakePln: payload.betAmount, over: payload.overValue }),
  })
  return {
    result: data.roll,
    won: data.won,
    payout: data.payout,
    balances: { PLN: data.balance },
  }
}

/** @param {{ betAmount: number; target: number }} payload */
export async function playLimbo(payload) {
  const data = await apiCall('/games/limbo', {
    method: 'POST',
    body: JSON.stringify({ stakePln: payload.betAmount, target: payload.target }),
  })
  return {
    result: data.crash,
    won: data.won,
    payout: data.payout,
    balances: { PLN: data.balance },
  }
}

function mapBlackjackResponse(data) {
  const out = {
    active: Boolean(data.active),
    reset: Boolean(data.reset),
    resumed: Boolean(data.resumed),
    phase: data.phase ?? 'idle',
    player: data.player ?? [],
    dealer: data.dealer ?? [],
    hands: data.hands ?? null,
    activeHand: data.activeHand ?? 0,
    split: Boolean(data.split),
    doubled: data.doubled ?? [false],
    canHit: data.canHit !== false,
    canDouble: Boolean(data.canDouble),
    canSplit: Boolean(data.canSplit),
    handOutcomes: data.handOutcomes ?? null,
    stakePln: data.stakePln ?? null,
    unitStakePln: data.unitStakePln ?? null,
    outcome: data.outcome ?? null,
    payout: data.payout ?? 0,
    multiplier: data.multiplier ?? 0,
  }
  if (data.balance != null) {
    out.balances = { PLN: data.balance }
  }
  return out
}

export async function fetchActiveBlackjack() {
  const data = await apiCall('/games/blackjack/active')
  return mapBlackjackResponse(data)
}

export async function resetBlackjack() {
  const data = await apiCall('/games/blackjack/reset', { method: 'POST', body: '{}' })
  return mapBlackjackResponse(data)
}

/** @param {{ betAmount: number }} payload */
export async function startBlackjack(payload) {
  const data = await apiCall('/games/blackjack/start', {
    method: 'POST',
    body: JSON.stringify({ stakePln: payload.betAmount }),
  })
  return mapBlackjackResponse(data)
}

export async function hitBlackjack() {
  const data = await apiCall('/games/blackjack/hit', { method: 'POST', body: '{}' })
  return mapBlackjackResponse(data)
}

export async function standBlackjack() {
  const data = await apiCall('/games/blackjack/stand', { method: 'POST', body: '{}' })
  return mapBlackjackResponse(data)
}

export async function doubleBlackjack() {
  const data = await apiCall('/games/blackjack/double', { method: 'POST', body: '{}' })
  return mapBlackjackResponse(data)
}

export async function splitBlackjack() {
  const data = await apiCall('/games/blackjack/split', { method: 'POST', body: '{}' })
  return mapBlackjackResponse(data)
}

/** @param {{ betAmount: number; uniqueCards: number }} payload */
export async function playBlitz(payload) {
  const data = await apiCall('/games/blitz', {
    method: 'POST',
    body: JSON.stringify({
      stakePln: payload.betAmount,
      uniqueCards: payload.uniqueCards,
    }),
  })
  return {
    won: data.won,
    picks: data.picks ?? [],
    multiplier: data.multiplier,
    payout: data.payout,
    balances: { PLN: data.balance },
  }
}

/** @param {{ betAmount: number; selected: number[] }} payload — UI cells 1–40 */
export async function playKeno(payload) {
  const picks = payload.selected.map((n) => n - 1)
  const data = await apiCall('/games/keno', {
    method: 'POST',
    body: JSON.stringify({ stakePln: payload.betAmount, picks }),
  })
  return {
    drawn: data.drawn.map((n) => n + 1),
    hits: data.hits,
    multiplier: data.multiplier,
    payout: data.payout,
    balances: { PLN: data.balance },
  }
}
