#!/usr/bin/env bash
# Stop only the processes launch.sh started, keep their logs next to the evidence, and remove the run dir.
RUN="${TMPDIR:-/tmp}/pnm-verify"
EVIDENCE="${TMPDIR:-/tmp}/pnm-verify-evidence"
[ -d "$RUN" ] || { echo "nothing to clean: $RUN does not exist"; exit 0; }

# What each process launch.sh started has in its command line. A PID whose command no longer
# matches has exited and been reused by the system for something else, so it is left alone.
signature() {
  case "$1" in
    backend) echo "uvicorn app.main:app --port 8100" ;;
    frontend) echo "vite.js --port 5174" ;;
    chrome) echo "--user-data-dir=$RUN/chrome-profile" ;;
  esac
}

for name in chrome frontend backend; do
  pid="$(cat "$RUN/$name.pid" 2>/dev/null)"
  if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
    if [[ "$(ps -o command= -p "$pid")" != *"$(signature "$name")"* ]]; then
      echo "skipped $name: PID $pid is now a different program"
      continue
    fi
    kill "$pid"
    for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.25; done
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid"
    echo "stopped $name ($pid)"
  fi
done

logs="$EVIDENCE/logs-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$logs" && cp "$RUN"/*.log "$logs"/ 2>/dev/null
rm -rf "$RUN"
echo "logs kept in $logs"
for port in 8100 5174 9223; do
  lsof -ti "tcp:$port" >/dev/null 2>&1 && echo "WARN port $port still in use by a process launch.sh did not start"
done
exit 0
