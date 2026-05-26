#!/usr/bin/env sh
# Install deps, validate .env, start API + bots (see scripts/start.sh)
set -e
cd "$(dirname "$0")/.."

echo "==> Backend deploy"

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    echo "No .env found — copying .env.example → .env"
    cp .env.example .env
    echo "Edit backend/.env before running in production."
  else
    echo "ERROR: backend/.env missing" >&2
    exit 1
  fi
fi

echo "==> npm install"
npm install

if [ ! -d .venv ]; then
  echo "==> Creating Python venv (.venv)"
  python3 -m venv .venv
fi

echo "==> pip install -r requirements.txt"
.venv/bin/pip install -q -r requirements.txt

echo "==> Checking .env"
.venv/bin/python scripts/check_env.py

PROD=false
case "${NODE_ENV:-development}" in
  production|prod) PROD=true ;;
esac

if [ "$PROD" = true ]; then
  echo "==> Production: starting API + bots (no reload)"
  exec sh scripts/start.sh
fi

echo "==> Development: starting API + bots (nodemon)"
exec npm start
