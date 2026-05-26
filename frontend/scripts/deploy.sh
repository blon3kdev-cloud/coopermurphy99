#!/usr/bin/env sh
# Install deps, validate env, start dev server or build for production
set -e
cd "$(dirname "$0")/.."

echo "==> Frontend deploy"

sh scripts/check_env.sh

echo "==> npm install"
npm install

PROD=false
case "${NODE_ENV:-development}" in
  production|prod) PROD=true ;;
esac

if [ "$PROD" = true ]; then
  echo "==> Production build"
  npm run build
  PORT="${PORT:-3000}"
  echo "==> Serving build on port ${PORT}"
  exec npx --yes serve -s build -l "$PORT"
fi

echo "==> Development: starting CRA dev server"
exec npm start
