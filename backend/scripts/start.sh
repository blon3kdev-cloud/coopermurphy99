#!/usr/bin/env sh
# Start API + Discord / Telegram bots when tokens are set in .env
set -e
cd "$(dirname "$0")/.."

DISCORD_PID=""
TELEGRAM_PID=""
cleanup() {
  for pid in "$DISCORD_PID" "$TELEGRAM_PID"; do
    if [ -n "$pid" ]; then
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap cleanup INT TERM EXIT

if ! command -v tesseract >/dev/null 2>&1; then
  echo "WARNING: tesseract not in PATH — BLIK image OCR disabled."
  echo "  macOS: brew install tesseract tesseract-lang"
  echo "  Debian/Ubuntu: sudo apt install tesseract-ocr tesseract-ocr-pol"
fi

if [ -f .env ]; then
  DISCORD_TOKEN=$(grep -E '^DISCORD_TOKEN=' .env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
  TELEGRAM_TOKEN=$(grep -E '^TELEGRAM_TOKEN=' .env | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | xargs)
fi

if [ -n "$DISCORD_TOKEN" ]; then
  if pgrep -f "bots/discord_bot.py" >/dev/null 2>&1; then
    echo "Stopping previous Discord bot instance(s)..."
    pkill -f "bots/discord_bot.py" 2>/dev/null || true
    sleep 1
  fi
  echo "Starting Discord bot..."
  .venv/bin/python bots/discord_bot.py &
  DISCORD_PID=$!
else
  echo "DISCORD_TOKEN not set — skipping Discord bot."
fi

if [ -n "$TELEGRAM_TOKEN" ]; then
  if pgrep -f "bots/telegram_bot.py" >/dev/null 2>&1; then
    echo "Stopping previous Telegram bot instance(s)..."
    pkill -f "bots/telegram_bot.py" 2>/dev/null || true
    sleep 1
  fi
  echo "Starting Telegram bot..."
  .venv/bin/python bots/telegram_bot.py &
  TELEGRAM_PID=$!
else
  echo "TELEGRAM_TOKEN not set — skipping Telegram bot."
fi

# No `exec` — keeps trap so nodemon restarts also stop the bots.
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-4000}"
