#!/data/data/com.termux/files/usr/bin/bash
export BRO=~/broccoli PYTHONPATH=$BRO/lib RISH_APPLICATION_ID=com.termux
export BROCCOLI_GROK_PKG=ai.x.grok BROCCOLI_NO_ENTER=1 BROCCOLI_SEND_MODE=sibling_first
TASK="${1:-BROCC_TASK reply exactly: LOOP_OK}"
termux-clipboard-set "$TASK"
python3 -c "
import sys,json,os
sys.path.insert(0,'$BRO/lib')
os.environ['BROCCOLI_NO_ENTER']='1'
from broccoli_core_round import full_round
print(json.dumps(full_round('$TASK'), indent=2))
"
grep -E 'send_adb|inject|round ok' "$BRO/reports/infinite.log" | tail -8
