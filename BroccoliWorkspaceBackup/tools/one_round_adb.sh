#!/data/data/com.termux/files/usr/bin/bash
export BRO="${BRO:-$HOME/broccoli}"
export PYTHONPATH="$BRO/lib"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
export BROCCOLI_GROK_PKG="${BROCCOLI_GROK_PKG:-ai.x.grok}"
export BROCCOLI_NO_ENTER=1
TASK="${1:-BROCC_WALK reply exactly: LOOP_OK}"
termux-clipboard-set "$TASK" 2>/dev/null || true
printf '%s\n' "$TASK" > "$BRO/inbox/prompt.txt"
python3 -c "
import sys, json
sys.path.insert(0, '$BRO/lib')
from broccoli_core_round import full_round
print(json.dumps(full_round('$TASK'), indent=2))
"
