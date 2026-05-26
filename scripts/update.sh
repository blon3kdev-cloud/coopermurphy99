#!/usr/bin/env sh
# Pull latest from GitHub, refresh deps in backend + frontend, then redeploy
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

DEFAULT_ORIGIN="git@github.com:blon3kdev-cloud/coopermurphy99.git"

echo "==> Update: pull latest from GitHub"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: not a git repository — clone first: git clone $DEFAULT_ORIGIN" >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "==> Adding origin: $DEFAULT_ORIGIN"
  git remote add origin "$DEFAULT_ORIGIN"
fi

BRANCH="$(git branch --show-current 2>/dev/null || true)"
if [ -z "$BRANCH" ]; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi

if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "WARN: uncommitted local changes — pull may require merge or stash"
fi

git fetch origin
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git pull --ff-only origin "$BRANCH" || git pull origin "$BRANCH"
else
  echo "WARN: origin/$BRANCH not found — pulling default branch"
  git pull --ff-only origin || git pull origin
fi

echo "==> Update backend dependencies"
cd "$ROOT/backend"
npm install
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

echo "==> Update frontend dependencies"
cd "$ROOT/frontend"
npm install

echo "==> Stopping previous dev processes (if any)"
pkill -f "react-scripts start" 2>/dev/null || true
pkill -f "bots/discord_bot.py" 2>/dev/null || true
pkill -f "bots/telegram_bot.py" 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true
sleep 1

echo "==> Redeploy"
cd "$ROOT"
exec npm run deploy
