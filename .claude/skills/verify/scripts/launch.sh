#!/usr/bin/env bash
# Start a private copy of the app for verification and wait until it is usable:
# backend on :8100, frontend on :5174 (proxying /api to :8100), headless Chrome with CDP on :9223.
# Claude is off unless VERIFY_CLAUDE=1, which uses the key in backend/.env and costs money.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../../.." && pwd)"
RUN="${TMPDIR:-/tmp}/pnm-verify"
BACKEND_PORT=8100
FRONTEND_PORT=5174
CDP_PORT=9223
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

for port in $BACKEND_PORT $FRONTEND_PORT $CDP_PORT; do
  if lsof -ti "tcp:$port" >/dev/null 2>&1; then
    echo "FAIL port $port is already in use. If it is ours, run cleanup.sh; never stop someone else's process." >&2
    exit 1
  fi
done
[ -x "$ROOT/backend/.venv/bin/uvicorn" ] || { echo "FAIL backend/.venv is missing; see README" >&2; exit 1; }
[ -d "$ROOT/frontend/node_modules/vite" ] || { echo "FAIL run npm install in frontend first" >&2; exit 1; }
[ -x "$CHROME" ] || { echo "FAIL Chrome not found at $CHROME; set CHROME=/path/to/chrome" >&2; exit 1; }

rm -rf "$RUN"
mkdir -p "$RUN"

# Offline when the model is cached, so start-up never waits on huggingface.co.
if [ -d "$HOME/.cache/huggingface/hub/models--ProsusAI--finbert" ]; then offline=1; else offline=0; fi
cd "$ROOT/backend"
if [ "${VERIFY_CLAUDE:-0}" = 1 ]; then
  HF_HUB_OFFLINE=$offline nohup .venv/bin/uvicorn app.main:app --port $BACKEND_PORT >"$RUN/backend.log" 2>&1 &
else
  ANTHROPIC_API_KEY="" ANTHROPIC_AUTH_TOKEN="" HF_HUB_OFFLINE=$offline \
    nohup .venv/bin/uvicorn app.main:app --port $BACKEND_PORT >"$RUN/backend.log" 2>&1 &
fi
echo $! >"$RUN/backend.pid"

cd "$ROOT/frontend"
API_URL="http://localhost:$BACKEND_PORT" nohup node node_modules/vite/bin/vite.js --port $FRONTEND_PORT --strictPort \
  >"$RUN/frontend.log" 2>&1 &
echo $! >"$RUN/frontend.pid"

nohup "$CHROME" --headless=new --remote-debugging-port=$CDP_PORT --user-data-dir="$RUN/chrome-profile" \
  --no-first-run --no-default-browser-check --window-size=1280,900 about:blank >"$RUN/chrome.log" 2>&1 &
echo $! >"$RUN/chrome.pid"

for _ in $(seq 1 180); do
  health="$(curl -s -m 2 "http://localhost:$FRONTEND_PORT/api/health" || true)"
  if [[ "$health" == *'"finbert":"ready"'* ]] && curl -s -m 2 "http://127.0.0.1:$CDP_PORT/json/version" >/dev/null; then
    echo "READY app=http://localhost:$FRONTEND_PORT health=$health"
    exit 0
  fi
  sleep 1
done
echo "FAIL not ready after 180 s; see $RUN/*.log, then run cleanup.sh" >&2
exit 1
