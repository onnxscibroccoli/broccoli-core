#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BRO="${BRO:-$HOME/broccoli}"
export BRO PYTHONPATH="$BRO/lib" RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
export BROCCOLI_PROGRAMMATIC=1
rm -f "$BRO/state/STOP" "$BRO/state/PAUSE"
mkdir -p "$BRO/reports"
python3 "$BRO/tools/agentic_run_once.py"
pgrep -f broccoli_agentic_loop.py >/dev/null || nohup python3 "$BRO/tools/broccoli_agentic_loop.py" >>"$BRO/reports/agentic_loop.log" 2>&1 &
pgrep -af broccoli_agentic_loop || true
tail -10 "$BRO/reports/agentic.log" 2>/dev/null || true
echo PROGRAMMATIC_ON_OK
