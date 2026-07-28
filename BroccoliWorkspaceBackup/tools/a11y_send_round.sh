#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
APP="${BROCC_CHAT_APP:-grok}"
TASK="${1:-BROCC_TASK reply exactly: LOOP_OK}"
BRO="$HOME/broccoli"
printf '%s' "$TASK" | termux-clipboard-set
printf '%s\n' "$TASK" > "$HOME/brocc-inbox/prompt.txt"
printf '%s\n' "$TASK" > "$BRO/inbox/prompt.txt"

# Prefer your proven inject path
if command -v brocc >/dev/null 2>&1; then
  brocc autoheal 2>/dev/null | tee -a "$BRO/reports/a11y_send.log" | grep -q 'AUTOHEAL_OK ok=True' && { echo A11Y_SEND autoheal_ok; exit 0; }
fi
if [ -f "$HOME/broccoli_autoheal.py" ]; then
  python3 "$HOME/broccoli_autoheal.py" 2>/dev/null | grep -q 'ok=True' && { echo A11Y_SEND autoheal_py_ok; exit 0; }
fi

python3 "$BRO/lib/a11y_automation.py" send_clip <<<"$TASK" && echo A11Y_SEND paste_ok
