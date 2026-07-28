#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/agent_tick.log"
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

P="$(head -1 "$HOME/broccoli/queue/pending.txt" 2>/dev/null | sed 's/^ASK|//' || true)"
[ -n "$P" ] || { log "empty_queue"; exit 0; }

log "send len=${#P}"
if REPLY="$(bash "$HOME/broccoli/tools/wire_send_ui.sh" "$P" 2>>"$LOG")"; then
  log "reply=${REPLY:0:100}"
  echo "$REPLY" >> "$HOME/broccoli/thread/grok_last.txt"
  FP="$(python3 "$HOME/broccoli/tools/phrase_grok_dump.py" fp 2>/dev/null || true)"
  [ -n "$FP" ] && echo "$FP" > "$HOME/broccoli/meta/last_consumed_fp"
  echo "$REPLY" > "$HOME/broccoli/meta/last_consumed_reply"
  [ -x "$HOME/broccoli/tools/agent_consume_iteration.sh" ] && bash "$HOME/broccoli/tools/agent_consume_iteration.sh" "$P" "$REPLY" >>"$LOG" 2>&1 || true
  tail -n +2 "$HOME/broccoli/queue/pending.txt" > "$HOME/broccoli/queue/pending.txt.tmp" 2>/dev/null && mv -f "$HOME/broccoli/queue/pending.txt.tmp" "$HOME/broccoli/queue/pending.txt" || true
  exit 0
fi
log "wire_fail"
exit 1
