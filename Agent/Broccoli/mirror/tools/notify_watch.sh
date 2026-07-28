#!/data/data/com.termux/files/usr/bin/bash
# Background: periodic status + notify when new phrased reply (dump/fingerprint).
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/notify_watch.log"
STOP="$HOME/broccoli/meta/NOTIFY_STOP"
INTERVAL="${NOTIFY_INTERVAL_SEC:-90}"
FP_FILE="$HOME/broccoli/meta/last_notify_fp"
IDLE_FILE="$HOME/broccoli/meta/last_wire_activity"

log(){ echo "$(date -Iseconds) $*" >> "$LOG"; }

touch_activity(){
  date +%s > "$IDLE_FILE"
}

log "notify_watch start interval=${INTERVAL}s"
bash "$HOME/broccoli/tools/notify_status.sh"

while [ ! -f "$STOP" ]; do
  bash "$HOME/broccoli/tools/notify_status.sh"

  NOW=$(date +%s)
  LAST_ACT=0
  [ -f "$IDLE_FILE" ] && LAST_ACT=$(cat "$IDLE_FILE" 2>/dev/null || echo 0)
  IDLE_SEC=$((NOW - LAST_ACT))

  if [ "$IDLE_SEC" -gt 300 ] && pgrep -f agent_daemon.sh >/dev/null 2>&1; then
    bash "$HOME/broccoli/lib/notify.sh" "Broccoli · idle" "Agent running but no wire activity ${IDLE_SEC}s — Grok FG?" 0
  fi

  if [ -x "$HOME/broccoli/tools/phrase_grok_dump.py" ]; then
    bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || true
    FP="$(python3 "$HOME/broccoli/tools/phrase_grok_dump.py" fp 2>/dev/null || true)"
    PREV="$(cat "$FP_FILE" 2>/dev/null || true)"
    if [ -n "$FP" ] && [ "$FP" != "$PREV" ]; then
      echo "$FP" > "$FP_FILE"
      bash "$HOME/broccoli/tools/notify_from_dump.sh" >>"$LOG" 2>&1 || true
      touch_activity
      log "new_chat_fp"
    fi
  fi

  sleep "$INTERVAL"
done
log "notify_watch stop"
