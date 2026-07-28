#!/data/data/com.termux/files/usr/bin/bash
set -u
HOME_BR="$HOME/broccoli"
WORKER="$HOME/broccoli_worker.sh"
LOG="$HOME_BR/reports/daemon.log"
mkdir -p "$HOME_BR/reports"

_run_front() {
  if [[ ! -x "$WORKER" ]]; then
    echo "$(date): worker missing: $WORKER" >>"$LOG"
    return 1
  fi
  bash "$WORKER" >>"$LOG" 2>&1
}

echo "daemon $$ $(date)" >>"$LOG"
python3 "$HOME/broccoli_pulse.py" stop 2>/dev/null
python3 "$HOME/broccoli_pulse.py" loop 7 >>"$LOG" 2>&1 &
while true; do
  _run_front || true
  sleep 15
done
