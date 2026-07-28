#!/data/data/com.termux/files/usr/bin/bash
# When queue empty: rish dump -> if new chat fingerprint vs last consumed, iterate.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LAST_FP="$HOME/broccoli/meta/last_consumed_fp"
LAST_REPLY="$HOME/broccoli/meta/last_consumed_reply"
LOG="$HOME/broccoli/reports/agent_watch.log"

[ -x "$HOME/broccoli/lib/ui_dump_rish.sh" ] || exit 0
[ -x "$HOME/broccoli/tools/phrase_grok_dump.py" ] || exit 0

bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || exit 0
FP="$(python3 "$HOME/broccoli/tools/phrase_grok_dump.py" fp 2>/dev/null || true)"
REPLY="$(python3 "$HOME/broccoli/tools/phrase_grok_dump.py" last 2>/dev/null || true)"
[ -z "$FP" ] && exit 0
[ -z "$REPLY" ] && exit 0

PREV_FP="$(cat "$LAST_FP" 2>/dev/null || true)"
PREV_REPLY="$(cat "$LAST_REPLY" 2>/dev/null || true)"

# New assistant content in Grok UI (any context window visible in dump)
if [ "$FP" != "$PREV_FP" ] && [ "$REPLY" != "$PREV_REPLY" ]; then
  echo "$(date -Iseconds) new_chat fp=$FP reply=${REPLY:0:60}" >> "$LOG"
  echo "$REPLY" >> "$HOME/broccoli/thread/grok_last.txt"
  echo "$FP" > "$LAST_FP"
  echo "$REPLY" > "$LAST_REPLY"
  if [ -x "$HOME/broccoli/tools/agent_consume_iteration.sh" ]; then
    bash "$HOME/broccoli/tools/agent_consume_iteration.sh" "" "$REPLY" >>"$LOG" 2>&1 || true
  fi
  exit 0
fi
exit 0
