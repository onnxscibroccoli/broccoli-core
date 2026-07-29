#!/data/data/com.termux/files/usr/bin/bash
export BRO=~/broccoli PYTHONPATH=$BRO/lib RISH_APPLICATION_ID=com.termux
export BROCCOLI_GROK_PKG=ai.x.grok BROCCOLI_NO_ENTER=1
pkill -f broccoli_infinite_dev_loop.py 2>/dev/null || true
rm -f "$BRO/state/STOP" "$BRO/state/PAUSE"
TASK="${1:-BROCC_TASK reply exactly: LOOP_OK}"
printf '%s\n' "$TASK" > "$BRO/inbox/prompt.txt"
termux-clipboard-set "$TASK" 2>/dev/null || true
touch "$BRO/inbox/trigger"
nohup python3 "$BRO/tools/broccoli_infinite_dev_loop.py" >>"$BRO/reports/infinite_nohup.log" 2>&1 &
echo "pid=$! tail -f $BRO/reports/infinite.log"
