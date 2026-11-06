#!/usr/bin/env sh
# Production start (Render). First boot builds the database on the persistent disk (~10 min) while the API
# already answers (health checks pass), then restarts once so every cache sees the full data.
set -e
cd "$(dirname "$0")"
DB="${KINCARE_DB:-../data/kincare.db}"
PORT="${PORT:-8000}"

if [ ! -s "$DB" ] || [ "$(python -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('select count(*) from sqlite_master where name=\'medicines\'').fetchone()[0])" "$DB" 2>/dev/null)" != "1" ]; then
  echo "First boot: building the KinCare database at $DB"
  uvicorn main:app --host 0.0.0.0 --port "$PORT" &
  API=$!
  python -m ingest.portal || python -m ingest.portal      # 6,865 CDSCO + state alerts (retry once: the portal is flaky)
  python -m ingest.medicines                               # 246k Indian brands with prices
  python -m ingest.bidmc --waves 0 || true                 # ICU replay records (optional)
  echo "Database ready, restarting the API"
  kill "$API" && wait "$API" 2>/dev/null || true
fi

exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
