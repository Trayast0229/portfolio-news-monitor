#!/usr/bin/env bash
# Read-only: is the verification instance from launch.sh up, ours, and usable? Exit 0 only if every line is OK.
RUN="${TMPDIR:-/tmp}/pnm-verify"
status=0
check() { if eval "$2" >/dev/null 2>&1; then echo "OK   $1"; else echo "FAIL $1"; status=1; fi; }
owns() { [ -f "$RUN/$1.pid" ] && lsof -ti "tcp:$2" 2>/dev/null | grep -qx "$(cat "$RUN/$1.pid")"; }

check "backend :8100 is the process launch.sh started" "owns backend 8100"
check "frontend :5174 is the process launch.sh started" "owns frontend 5174"
check "chrome :9223 is the process launch.sh started" "owns chrome 9223"
health="$(curl -s -m 3 http://localhost:5174/api/health)"
echo "     health via frontend proxy: ${health:-<no reply>}"
check "FinBERT ready" '[[ "$health" == *"\"finbert\":\"ready\""* ]]'
check "Claude off (no API cost)" '[[ "$health" == *"\"claude\":\"unavailable\""* ]] || [ "${VERIFY_CLAUDE:-0}" = 1 ]'
check "frontend serves the app" 'curl -s -m 3 http://localhost:5174/ | grep -q "<div id=\"root\">"'
check "chrome DevTools answers" "curl -s -m 3 http://127.0.0.1:9223/json/version"
exit $status
