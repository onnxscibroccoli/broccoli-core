#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/loop.log"
while true; do
  echo "=== $(date -Iseconds) ===" >> "$LOG"
  bash "$HOME/broccoli/tools/codevel_wire_fast.sh" in >> "$LOG" 2>&1 || true
  sleep 8
done
