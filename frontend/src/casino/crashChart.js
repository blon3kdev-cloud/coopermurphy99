/** Canvas chart for the crash multiplier curve (exponential growth). */

export const CHART_PAD = 28

const MIN_TIME_WINDOW = 2.8
const MIN_MULT_SPAN = 0.35
const LINE_WIDTH = 5.5
const HEAD_X_FRAC = 0.94
const HEAD_Y_FRAC = 0.86
const HEAD_RADIUS = 10

/** Multiplier tiers — blue ramp shifts brighter as the round climbs */
const MULT_TIERS = [
  {
    upTo: 2,
    lineBot: '#1e3a8a',
    lineMid: '#2563eb',
    lineTop: '#93c5fd',
    fillLo: 'rgba(30, 58, 138, 0.32)',
    fillMid: 'rgba(37, 99, 235, 0.42)',
    fillHi: 'rgba(147, 197, 253, 0.55)',
  },
  {
    upTo: 5,
    lineBot: '#1e40af',
    lineMid: '#3b82f6',
    lineTop: '#7dd3fc',
    fillLo: 'rgba(30, 64, 175, 0.3)',
    fillMid: 'rgba(59, 130, 246, 0.44)',
    fillHi: 'rgba(125, 211, 252, 0.58)',
  },
  {
    upTo: 10,
    lineBot: '#1d4ed8',
    lineMid: '#0ea5e9',
    lineTop: '#67e8f9',
    fillLo: 'rgba(29, 78, 216, 0.3)',
    fillMid: 'rgba(14, 165, 233, 0.44)',
    fillHi: 'rgba(103, 232, 249, 0.58)',
  },
  {
    upTo: 50,
    lineBot: '#3730a3',
    lineMid: '#6366f1',
    lineTop: '#a5b4fc',
    fillLo: 'rgba(55, 48, 163, 0.3)',
    fillMid: 'rgba(99, 102, 241, 0.44)',
    fillHi: 'rgba(165, 180, 252, 0.58)',
  },
  {
    upTo: Infinity,
    lineBot: '#312e81',
    lineMid: '#818cf8',
    lineTop: '#c7d2fe',
    fillLo: 'rgba(49, 46, 129, 0.3)',
    fillMid: 'rgba(129, 140, 248, 0.44)',
    fillHi: 'rgba(199, 210, 254, 0.58)',
  },
]

const CRASHED_PALETTE = {
  lineTop: '#fca5a5',
  lineBot: '#ef4444',
  fillHi: 'rgba(239, 68, 68, 0.34)',
  fillMid: 'rgba(200, 50, 50, 0.18)',
  fillLo: 'rgba(160, 40, 40, 0.1)',
}

/**
 * @param {number} growthRate Must match backend `crash_engine.GROWTH_RATE`
 */
export function multFromElapsed(sec, growthRate) {
  if (sec <= 0) return 1
  return Math.exp(growthRate * sec)
}

export function elapsedFromMult(m, growthRate) {
  if (m <= 1) return 0
  return Math.log(m) / growthRate
}

function paletteForMult(mult, crashed) {
  if (crashed) return CRASHED_PALETTE
  for (const tier of MULT_TIERS) {
    if (mult < tier.upTo) return tier
  }
  return MULT_TIERS[MULT_TIERS.length - 1]
}

/** Steeper on-screen curve as multiplier climbs (visual only). */
function curveGamma(headMult) {
  if (headMult <= 1.01) return 1
  return Math.max(0.58, 1 - Math.log10(headMult) * 0.11)
}

export function createCrashChart(growthRate) {
  let timeMax = MIN_TIME_WINDOW
  let multSpan = MIN_MULT_SPAN
  let lastHeadMult = 1

  function reset() {
    timeMax = MIN_TIME_WINDOW
    multSpan = MIN_MULT_SPAN
    lastHeadMult = 1
  }

  function fitViewport(elapsedSec, headMult) {
    lastHeadMult = headMult
    const tNeed = Math.max(MIN_TIME_WINDOW, elapsedSec / HEAD_X_FRAC)
    const lift = Math.max(0, headMult - 1)
    const gamma = curveGamma(headMult)
    const yFrac =
      headMult > 1.01
        ? Math.max(0.58, HEAD_Y_FRAC - Math.min(0.24, Math.log10(headMult) * 0.09))
        : HEAD_Y_FRAC
    /** raw^gamma = yFrac on screen — keep the head on its target row */
    const rawTarget = Math.pow(yFrac, 1 / gamma)
    const spanNeed = Math.max(MIN_MULT_SPAN, lift / rawTarget + 0.04)
    timeMax = Math.max(timeMax, tNeed)
    multSpan = Math.max(multSpan, spanNeed)
  }

  function plotRect(w, h) {
    return {
      left: CHART_PAD,
      top: CHART_PAD,
      right: w - CHART_PAD,
      bottom: h - CHART_PAD,
      width: w - CHART_PAD * 2,
      height: h - CHART_PAD * 2,
    }
  }

  function multToY(mult, plotH) {
    const span = Math.max(multSpan, 1e-6)
    const raw = Math.max(0, Math.min(1, (mult - 1) / span))
    const gamma = curveGamma(lastHeadMult)
    const curved = Math.pow(raw, gamma)
    return plotH * (1 - curved)
  }

  function toScreen(sec, mult, w, h) {
    const plot = plotRect(w, h)
    const tx = Math.max(0, Math.min(1, sec / Math.max(timeMax, 1e-6)))
    return {
      x: plot.left + tx * plot.width,
      y: plot.top + multToY(mult, plot.height),
    }
  }

  function sampleCurve(elapsedSec, steps) {
    const n = Math.min(240, Math.max(48, steps))
    const pts = [{ sec: 0, mult: 1 }]
    for (let i = 1; i <= n; i++) {
      const sec = (elapsedSec * i) / n
      pts.push({ sec, mult: multFromElapsed(sec, growthRate) })
    }
    return pts
  }

  function makeLineGradient(ctx, x0, y0, x1, y1, palette) {
    const g = ctx.createLinearGradient(x0, y0, x1, y1)
    g.addColorStop(0, palette.lineBot)
    g.addColorStop(0.35, palette.lineMid ?? palette.lineBot)
    g.addColorStop(0.72, palette.lineMid ?? palette.lineTop)
    g.addColorStop(1, palette.lineTop)
    return g
  }

  /** Fill under curve — dark blue at base, light blue at the head */
  function makeAreaGradient(ctx, origin, head, palette) {
    const g = ctx.createLinearGradient(origin.x, origin.y, head.x, head.y)
    g.addColorStop(0, palette.fillLo)
    g.addColorStop(0.28, palette.fillMid)
    g.addColorStop(0.62, palette.fillMid)
    g.addColorStop(0.88, palette.fillHi)
    g.addColorStop(1, palette.fillHi)
    return g
  }

  function drawHead(ctx, head) {
    ctx.beginPath()
    ctx.arc(head.x, head.y, HEAD_RADIUS, 0, Math.PI * 2)
    ctx.fillStyle = '#ffffff'
    ctx.fill()
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {{ elapsedSec: number, headMult: number, crashed: boolean }} params
   */
  function draw(ctx, w, h, { elapsedSec, headMult, crashed }) {
    if (w < 2 || h < 2 || elapsedSec <= 0) return

    const curveHeadMult = multFromElapsed(elapsedSec, growthRate)
    fitViewport(elapsedSec, Math.max(headMult, curveHeadMult))
    const plot = plotRect(w, h)
    const palette = paletteForMult(headMult, crashed)
    const origin = toScreen(0, 1, w, h)
    const pts = sampleCurve(elapsedSec, Math.ceil(elapsedSec * 55))

    const screenPts = pts.map((p) => {
      const { x, y } = toScreen(p.sec, p.mult, w, h)
      return { x, y }
    })

    const head = screenPts.length
      ? screenPts[screenPts.length - 1]
      : toScreen(elapsedSec, curveHeadMult, w, h)

    ctx.beginPath()
    ctx.moveTo(origin.x, origin.y)
    for (const p of screenPts) ctx.lineTo(p.x, p.y)
    ctx.lineTo(head.x, plot.bottom)
    ctx.lineTo(origin.x, plot.bottom)
    ctx.closePath()
    ctx.fillStyle = makeAreaGradient(ctx, { x: origin.x, y: plot.bottom }, head, palette)
    ctx.fill()

    ctx.beginPath()
    ctx.moveTo(origin.x, origin.y)
    for (const p of screenPts) ctx.lineTo(p.x, p.y)
    ctx.strokeStyle = makeLineGradient(ctx, origin.x, origin.y, head.x, head.y, palette)
    ctx.lineWidth = LINE_WIDTH
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
    ctx.stroke()

    drawHead(ctx, head)
  }

  return { reset, draw }
}
