#!/usr/bin/env sh
# Install + start backend and frontend together (from repo root)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cleanup() {
  if [ -n "$BACK_PID" ]; then kill "$BACK_PID" 2>/dev/null || true; fi
  if [ -n "$FRONT_PID" ]; then kill "$FRONT_PID" 2>/dev/null || true; fi
}
trap cleanup INT TERM EXIT

echo "==> Full stack deploy (backend + frontend)"
echo "    Stop with Ctrl+C"
echo ""

(cd "$ROOT/backend" && npm run deploy) &
BACK_PID=$!

(cd "$ROOT/frontend" && npm run deploy) &
FRONT_PID=$!

wait "$BACK_PID" "$FRONT_PID"
