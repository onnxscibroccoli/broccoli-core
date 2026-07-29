#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
APP="${BROCC_CHAT_APP:-grok}"
BRO="$HOME/broccoli"
OUT="$BRO/inbox/grok_reply.txt"
bash "$BRO/lib/shizuku_apps.sh" "$APP" foreground
sleep 1
bash "$BRO/lib/ui_dump_rish.sh"
export PYTHONPATH="$BRO/lib${PYTHONPATH:+:$PYTHONPATH}"
TEXT="$(python3 "$BRO/lib/a11y_automation.py" last)"
if [ -n "$TEXT" ]; then
  printf '%s\n' "$TEXT" > "$OUT"
  cp "$OUT" "$HOME/brocc-inbox/last_grok_reply.txt" 2>/dev/null || true
  echo "CONSUME_OK bytes=${#TEXT}"
else
  echo "CONSUME_FAIL"
  exit 1
fi
