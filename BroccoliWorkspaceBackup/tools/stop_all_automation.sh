#!/data/data/com.termux/files/usr/bin/bash
BRO="${BRO:-$HOME/broccoli}"
touch "$BRO/state/PAUSE" "$BRO/state/MANUAL_SEND"
pkill -f broccoli_agentic_loop.py 2>/dev/null || true
pkill -f poll_loop 2>/dev/null || true
pkill -f heal_daemon 2>/dev/null || true
echo STOPPED_ALL
pgrep -af broccoli_agentic || echo no_loop
