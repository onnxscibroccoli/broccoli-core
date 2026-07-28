#!/data/data/com.termux/files/usr/bin/bash
set -u
LOCK="$HOME/broccoli/reports/worker.lock"
mkdir -p "$(dirname "$LOCK")"
exec 9>"$LOCK"
flock -n 9 || { echo "[$(date)] worker skip" >> "$HOME/broccoli/reports/worker.log"; exit 0; }
LOG="$HOME/broccoli/reports/worker.log"
echo "[$(date)] worker start pid=$$" >>"$LOG"
"$HOME/brocc" run-once >>"$LOG" 2>&1
ec=$?
echo "[$(date)] worker exit=$ec pid=$$" >>"$LOG"
exit $ec
