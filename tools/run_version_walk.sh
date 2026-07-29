#!/data/data/com.termux/files/usr/bin/bash
export BRO="${BRO:-$HOME/broccoli}"
export PYTHONPATH="$BRO/lib"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
export BROCCOLI_GROK_PKG="${BROCCOLI_GROK_PKG:-ai.x.grok}"
pkill -f broccoli_agentic_loop.py 2>/dev/null || true
touch "$BRO/state/PAUSE"
python3 "$BRO/tools/version_walk_heal.py" 2>&1 | tee "$BRO/reports/version_walk_console.txt"
echo "--- tail log ---"
tail -25 "$BRO/reports/version_walk.log"
echo "--- winner ---"
cat "$BRO/meta/active_stack.json" 2>/dev/null || echo no_winner_yet
