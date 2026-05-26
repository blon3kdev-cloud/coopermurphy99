/**
 * Haptic feedback — no-op stub (web-haptics not bundled in this project).
 * Wire a real engine here when needed.
 * @param {string} [preset]
 */
export function haptic(preset = 'light') {
  if (navigator.vibrate) {
    const dur = preset === 'heavy' ? 40 : preset === 'medium' ? 20 : 10
    navigator.vibrate(dur)
  }
}
