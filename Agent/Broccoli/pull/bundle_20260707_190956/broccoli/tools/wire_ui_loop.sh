#!/data/data/com.termux/files/usr/bin/bash
# Poll UI dump until condition; max_sec is safety only.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
COND="${1:?cond: grok_fg|composer|msg_sent|reply_changed|fp_not FP}"
MSG="${2:-}"
MAX="${3:-45}"
LOG="$HOME/broccoli/reports/wire_ui_loop.log"
FP_BEFORE="${4:-}"
t=0
log(){ echo "$(date -Iseconds) wait $COND t=$t $*" | tee -a "$LOG"; }

while [ "$t" -lt "$MAX" ]; do
  bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || true
  ST="$(python3 "$HOME/broccoli/tools/ui_state.py" state "$MSG" 2>/dev/null || echo '{}')"
  case "$COND" in
    grok_fg)
      echo "$ST" | python3 -c "import sys,json; s=json.load(sys.stdin); sys.exit(0 if s.get('grok_fg') else 1)" && { log OK; exit 0; }
      ;;
    composer)
      echo "$ST" | python3 -c "import sys,json; s=json.load(sys.stdin); sys.exit(0 if s.get('has_composer') else 1)" && { log OK; exit 0; }
      ;;
    msg_sent)
      echo "$ST" | python3 -c "import sys,json; s=json.load(sys.stdin); sys.exit(0 if s.get('msg_in_chat') or s.get('composer_has_msg') else 1)" && { log OK; exit 0; }
      ;;
    reply_changed)
      FP="$(python3 "$HOME/broccoli/tools/ui_state.py" fp 2>/dev/null || echo x)"
      LAST="$(python3 "$HOME/broccoli/tools/ui_state.py" last 2>/dev/null || true)"
      if [ -n "$FP_BEFORE" ] && [ "$FP" != "$FP_BEFORE" ] && [ -n "$LAST" ]; then
        if [ -n "$MSG" ] && [ "$LAST" = "$MSG" ]; then
          : # still user bubble only
        else
          log OK "fp=$FP last_len=${#LAST}"
          echo "$LAST"
          exit 0
        fi
      fi
      ;;
    fp_not)
      FP="$(python3 "$HOME/broccoli/tools/ui_state.py" fp 2>/dev/null)"
      [ "$FP" != "$FP_BEFORE" ] && [ -n "$FP_BEFORE" ] && { log OK; exit 0; }
      ;;
  esac
  sleep 0.6
  t=$((t+1))
done
log TIMEOUT
exit 1
