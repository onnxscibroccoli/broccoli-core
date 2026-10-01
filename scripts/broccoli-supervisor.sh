#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${BROCCOLI_ROOT:-$HOME/broccoli-core}"
PREFIX_DIR="${PREFIX:-/data/data/com.termux/files/usr}"
PYTHON="${BROCCOLI_PYTHON:-$PREFIX_DIR/bin/python3}"
LOG_DIR="$ROOT/reports"
PID_FILE="$ROOT/runtime-supervisor.pid"
LOCK_DIR="$ROOT/runtime-supervisor.lock"
LOG_FILE="$LOG_DIR/runtime-supervisor.log"
INTERVAL="${BROCCOLI_SUPERVISOR_INTERVAL:-5}"

mkdir -p "$LOG_DIR"
cd "$ROOT"
log() { printf '%s %s\n' "$(date -Iseconds)" "$*" >> "$LOG_FILE"; }

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  old="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [ -n "$old" ] && kill -0 "$old" 2>/dev/null; then
    log "ALREADY_RUNNING pid=$old"
    exit 0
  fi
  rm -rf "$LOCK_DIR"
  mkdir "$LOCK_DIR"
fi
printf "%s\n" "${BASHPID}" > "$LOCK_DIR/pid"

if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock >/dev/null 2>&1 || true
  log "WAKE_LOCK requested"
fi

child_alive() {
  [ -f "$ROOT/runtime.pid" ] || return 1
  local pid args
  pid="$(cat "$ROOT/runtime.pid" 2>/dev/null || true)"
  [ -n "$pid" ] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  case "$args" in
    *"$ROOT/runtime/main.py"*) return 0 ;;
    *) return 1 ;;
  esac
}

start_child() {
  if child_alive; then return 0; fi
  nohup env PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}" "$PYTHON" -u "$ROOT/runtime/main.py" >> "$ROOT/runtime.log" 2>&1 &
  local pid=$!
  printf "%s\n" "$pid" > "$ROOT/runtime.pid"
  log "START child pid=$pid"
}

cleanup() {
  if command -v termux-wake-unlock >/dev/null 2>&1; then termux-wake-unlock >/dev/null 2>&1 || true; fi
  if [ -f "$LOCK_DIR/pid" ] && [ "$(cat "$LOCK_DIR/pid" 2>/dev/null || true)" = "${BASHPID}" ]; then
    rm -rf "$LOCK_DIR"
  fi
  log "STOP supervisor"
}

trap cleanup INT TERM EXIT
log "START supervisor pid=$$ root=$ROOT"
while :; do
  start_child
  sleep "$INTERVAL"
done
