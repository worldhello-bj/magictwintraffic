#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f web/dist/index.html ]; then echo 'Build viewer first: cd web && npm ci && npm run build' >&2; exit 1; fi
exec python -m http.server "${PORT:-8080}" --bind 127.0.0.1 --directory web/dist
