#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
R="$B/rish.sh"
SD="/sdcard/broccoli_window_dump.xml"
OUT="$B/window_dump.xml"
MAX="${WAIT_REPLY_MAX:-180}"
POLL="${WAIT_REPLY_POLL:-4}"
log(){ echo "[$(date -Iseconds)] wait: $*" >> "$B/wait_reply.log"; }

dump(){
  "$R" -c "uiautomator dump $SD" >>"$B/wait_reply.log" 2>&1 || true
  sleep 0.5
  [ -r "$SD" ] && cp -f "$SD" "$OUT"
}

# Scroll to bottom so latest assistant message is on screen
nudge_bottom(){
  "$R" -c "input swipe 540 1800 540 400 300" >>"$B/wait_reply.log" 2>&1 || true
  sleep 0.6
}

log "start max=${MAX}s"
elapsed=0
while [ "$elapsed" -lt "$MAX" ]; do
  bash "$B/ensure_grok_window.sh" >>"$B/wait_reply.log" 2>&1 || true
  nudge_bottom
  dump
  # Stop generating = still busy
  if grep -q 'Stop generating\|Stop response\|content-desc="Stop' "$OUT" 2>/dev/null; then
    log "still generating"
    sleep "$POLL"
    elapsed=$((elapsed + POLL))
    continue
  fi
  # Copy message on assistant bubble = ready
  if grep -q 'content-desc="Copy message"' "$OUT" 2>/dev/null; then
    log "ready (Copy message visible)"
    exit 0
  fi
  sleep "$POLL"
  elapsed=$((elapsed + POLL))
done
log "timeout"
exit 1
