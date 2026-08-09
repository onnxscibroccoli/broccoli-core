#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HOME}/broccoli-core"
META="${ROOT}/meta/always_on"
mkdir -p "$META"
log() { echo "$(date -Is) $*" | tee -a "$META/supervisor.log"; }
if [ -f "$META/runtime.pid" ]; then
  pid=$(cat "$META/runtime.pid" 2>/dev/null || true)
  if [ -n "${pid:-}" ] && kill -0 "$pid" 2>/dev/null; then
    log "STOP runtime pid=$pid"
    kill -INT "$pid" 2>/dev/null || true
    sleep 2
    kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  fi
  rm -f "$META/runtime.pid"
fi
if [ -f "$META/supervisor.pid" ]; then
  spid=$(cat "$META/supervisor.pid" 2>/dev/null || true)
  if [ -n "${spid:-}" ] && kill -0 "$spid" 2>/dev/null; then
    log "STOP supervisor pid=$spid"
    kill "$spid" 2>/dev/null || true
  fi
  rm -f "$META/supervisor.pid"
fi
log "always_on stopped"
