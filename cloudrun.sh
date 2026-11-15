#!/usr/bin/env bash
# Cloud Run entrypoint: API on 127.0.0.1:8000 (private), website on $PORT (public). If either exits, the container exits
# and Cloud Run restarts it.
set -e
PORT="${PORT:-8080}"
cd /app/api
uvicorn main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips='*' &
API=$!
cd /app/web
node node_modules/next/dist/bin/next start -H 0.0.0.0 -p "$PORT" &
WEB=$!
wait -n "$API" "$WEB"
exit 1
