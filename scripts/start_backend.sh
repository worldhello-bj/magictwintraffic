#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
PYTHON=python
if [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python; fi
exec "$PYTHON" -m uvicorn traffic_twin.api:app --host 127.0.0.1 --port "${PORT:-8000}" --workers 1
