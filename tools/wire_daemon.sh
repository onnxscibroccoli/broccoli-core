#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/wire_daemon.log"
STOP="$HOME/broccoli/meta/WIRE_STOP"
Q="$HOME/broccoli/queue/pending.txt"
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

idle_ok(){
  S="$(bash "$HOME/broccoli/lib/user_idle_sec.sh" 2>/dev/null || echo 5)"
  [ "${S:-0}" -ge 3 ]
}

round(){
  LINE="$(grep -v '^#' "$Q" 2>/dev/null | head -1 || true)"
  [ -n "$LINE" ] || return 0
  case "$LINE" in ASK|*) PROMPT="${LINE#ASK|}" ;; *) PROMPT="$LINE" ;; esac
  log "ROUND start"
  bash "$HOME/broccoli/tools/wire_send_ui.sh" "$PROMPT" >>"$LOG" 2>&1 || log "round fail rc=$?"
  [ -x "$HOME/broccoli/tools/extract_grok_code.py" ] && python3 "$HOME/broccoli/tools/extract_grok_code.py" >>"$LOG" 2>&1 || true
  NEW="$(ls -t "$HOME/broccoli/sandbox/from_grok"/block_*.sh 2>/dev/null | head -1 || true)"
  [ -n "$NEW" ] && [ -s "$NEW" ] && bash "$NEW" >>"$LOG" 2>&1 || true
  echo "$(date -Iseconds) done" >> "$HOME/broccoli/queue/done.txt"
  tail -n +2 "$Q" > "$Q.tmp" 2>/dev/null && mv -f "$Q.tmp" "$Q" || true
}

log "DAEMON start pid=$$"
while [ ! -f "$STOP" ]; do
  if idle_ok; then
    if [ -s "$Q" ]; then round || true
    else bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || true
    fi
  fi
  bash "$HOME/broccoli/tools/user_touch_watch.sh" 2>/dev/null || true
  sleep 0.8
done
log "DAEMON stop"
