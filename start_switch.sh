#!/usr/bin/env bash
# KinCare on Switch, for macOS and Linux (start_switch.bat does the same on Windows).
# Sets up KinCare (first run), starts its API, then the Recall Watcher.
# Switch Console must be open (it runs the Switch server and the Claude Code agents).
set -e
cd "$(dirname "$0")"
ROOT="$(pwd)"

PY="$ROOT/api/.venv/bin/python"
[ -x "$PY" ] || PY="$ROOT/api/.venv/Scripts/python"   # Git Bash on Windows
if [ ! -x "$PY" ]; then
  echo "[1/3] First run: creating the Python environment..."
  BASE="$(command -v python3.12 || command -v python3 || command -v python)" || { echo "Python 3.12 not found. Install it from python.org"; exit 1; }
  "$BASE" -m venv api/.venv
  PY="$ROOT/api/.venv/bin/python"
  [ -x "$PY" ] || PY="$ROOT/api/.venv/Scripts/python"
  "$PY" -m pip install -q -r api/requirements.txt
fi

if [ ! -f data/kincare.db ]; then
  echo "[1/3] Loading real CDSCO alerts and 246k medicine brands. A few minutes, once..."
  (cd api && "$PY" -m ingest.fetch --limit 24 && "$PY" -m ingest.load && "$PY" -m ingest.portal && "$PY" -m ingest.medicines)
else
  echo "[1/3] KinCare data ready"
fi

up() { "$PY" -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=2)" 2>/dev/null; }
if up; then
  echo "[2/3] KinCare API already running"
else
  echo "[2/3] Starting KinCare API on http://localhost:8000 (log: api/uvicorn.log)"
  (cd api && nohup "$PY" -m uvicorn main:app --port 8000 > uvicorn.log 2>&1 &)
fi
echo "Waiting for the API..."
until up; do sleep 2; done

if [ ! -f switch/.env ]; then
  cp switch/.env.example switch/.env
  echo
  echo "switch/.env created. Fill SWITCH_URL and SWITCH_REGISTRATION_KEY, then run:"
  echo "   \"$PY\" switch/recall_watcher.py register"
  echo "and add \"kincare-recall-watcher\" to the family room in Switch Console. Then run this file again."
  exit 0
fi

if ! grep -Eq '^SWITCH_AGENT_KEY=.+' switch/.env; then
  echo
  echo "The Recall Watcher is not registered yet. Fill SWITCH_URL and SWITCH_REGISTRATION_KEY in switch/.env, then:"
  echo "   \"$PY\" switch/recall_watcher.py register"
  echo "Meanwhile, try the whole flow offline:  \"$PY\" switch/demo_local.py"
  exit 0
fi

echo "[3/3] Starting the Recall Watcher (checks the family's medicines every few minutes). Ctrl+C stops it."
"$PY" -m pip install -q -r switch/requirements.txt
echo "KinCare is running. In Telegram, send a strip photo to the family group and @kincare-scan."
exec "$PY" switch/recall_watcher.py listen
