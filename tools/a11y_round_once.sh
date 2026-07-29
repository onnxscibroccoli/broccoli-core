#!/data/data/com.termux/files/usr/bin/bash
export BRO="${BRO:-$HOME/broccoli}"
export PYTHONPATH="$BRO/lib"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
TASK="${1:-BROCC_TASK reply exactly: LOOP_OK}"
termux-clipboard-set "$TASK" 2>/dev/null || true
printf '%s\n' "$TASK" > "$BRO/inbox/prompt.txt"
python3 -c "
import sys, json
sys.path.insert(0, '$BRO/lib')
from broccoli_a11y_send import full_round_a11y
print(json.dumps(full_round_a11y('$TASK'), indent=2)[:4000])
"
