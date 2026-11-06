#!/usr/bin/env bash
# Run KinCare locally: API on :8000, web on :3000.
# First time: (cd api && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt) && (cd web && npm install)
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/api/.venv/Scripts/python"
[ -x "$PY" ] || PY="$ROOT/api/.venv/bin/python"
(cd "$ROOT/api" && "$PY" -m uvicorn main:app --reload --port 8000) &
(cd "$ROOT/web" && npm run dev) &
trap 'kill 0' EXIT
wait
