#!/data/data/com.termux/files/usr/bin/bash
set -eu
LOG="$HOME/broccoli/reports/heal_supervisor.log"
STOP="$HOME/broccoli/meta/HEAL_STOP"
INT="${HEAL_INTERVAL_SEC:-50}"
while [ ! -f "$STOP" ]; do
  [ -f "$HOME/broccoli/meta/AGENT_STOP" ] || bash "$HOME/broccoli/tools/agent_ensure_running.sh" >>"$LOG" 2>&1 || true
  sleep "$INT"
done
