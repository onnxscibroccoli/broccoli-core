#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
R="$B/rish.sh"
INBOX="$B/inbox_response.txt"
LOG="$B/copy_fetch.log"

log(){ echo "[$(date -Iseconds)] $*" >>"$LOG"; }

bash "$B/ensure_grok_window.sh" >>"$LOG" 2>&1 || exit 2
bash "$B/wait_reply.sh" >>"$LOG" 2>&1 || log "wait timeout — try copy anyway"

bash "$B/ui_pull.sh" 2>/dev/null || bash "$B/ui_grok.sh" >>"$LOG" 2>&1 || exit 2

python3 "$B/chat_copy_tap.py" >"$B/.copy_tap.json" 2>>"$LOG" || {
  log "no Copy target"
  exit 3
}
read -r X Y < <(python3 -c "import json;d=json.load(open('$B/.copy_tap.json'));print(d['x'],d['y'])")
log "tap Copy $X $Y"
"$R" -c "input tap $X $Y"
sleep 0.8

for i in $(seq 1 12); do
  T=$("$B/clipboard.sh" get 2>/dev/null || true)
  if [ -n "$T" ]; then
    printf '%s' "$T" > "$INBOX"
    log "inbox $(wc -c <"$INBOX") bytes"
    # Must look like machine block
    case "$T" in
      CMD:*|TASK_COMPLETE:*|WRITE_FILE:*) exit 0 ;;
    esac
    log "clip not machine block; still saved"
    exit 0
  fi
  sleep 0.4
done
log "empty clipboard"
exit 4
