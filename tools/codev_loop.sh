#!/data/data/com.termux/files/usr/bin/bash
# Persistent co-dev: investigate → optional gap → enqueue summary → keep daemon alive
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
INTERVAL="${1:-120}"
LOG="$HOME/broccoli/reports/codev_loop.log"
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }
log "codev_loop start interval=${INTERVAL}s"
while [ ! -f "$HOME/broccoli/meta/WIRE_STOP" ]; do
  bash "$HOME/broccoli/tools/investigate_system.sh --live" >>"$LOG" 2>&1 || true
  if [ -x "$HOME/broccoli/tools/gap_watch.sh" ]; then
    P="$(head -1 "$HOME/broccoli/queue/pending.txt" 2>/dev/null | sed 's/^ASK|//' || true)"
    bash "$HOME/broccoli/tools/gap_watch.sh" "$P" >>"$LOG" 2>&1 || true
  fi
  # Refresh co-dev pointer
  python3 -c "
import json
from pathlib import Path
from datetime import datetime, timezone
m=Path.home()/'broccoli/meta/codev_window.json'
d=json.loads(m.read_text()) if m.is_file() else {}
d['last_cycle']=datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')
d['status']='open'
m.write_text(json.dumps(d,indent=2))
"
  sleep "$INTERVAL"
done
log "codev_loop stop (WIRE_STOP)"
