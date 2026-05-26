#!/usr/bin/env sh
# Pre-flight checks for frontend deploy
set -e
cd "$(dirname "$0")/.."

if [ ! -f .env ] && [ ! -f .env.development ] && [ ! -f .env.local ]; then
  if [ -f .env.example ]; then
    echo "No .env found — copying .env.example → .env"
    cp .env.example .env
  else
    echo "ERROR: frontend/.env missing" >&2
    exit 1
  fi
fi

case "${NODE_ENV:-development}" in
  production|prod)
    if [ -f .env ]; then
      # shellcheck disable=SC1091
      . ./.env
    fi
    if [ -z "${REACT_APP_API_URL:-}" ]; then
      echo "WARN: REACT_APP_API_URL is empty — set it in frontend/.env for production builds"
    fi
    ;;
esac

echo "Frontend env check OK"
