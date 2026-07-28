#!/data/data/com.termux/files/usr/bin/bash
export BRO="${BRO:-$HOME/broccoli}"
export PATH="$PREFIX/bin:$BRO/bin:$BRO/tools:$PATH"
export PYTHONPATH="$BRO/lib"
export RISH_APPLICATION_ID=com.termux
export BROCCOLI_GROK_PKG=ai.x.grok
export BROCCOLI_NO_ENTER=1
export BROCCOLI_SEND_MODE=sibling_first
export BROCCOLI_POLL_SEC="${BROCCOLI_POLL_SEC:-45}"
LOCK="$BRO/state/infinite.lock"
mkdir -p "$BRO/state"
exec 9>"$LOCK"
flock -n 9 || { echo "already running"; pgrep -af broccoli_infinite_dev_loop; exit 0; }
rm -f "$BRO/state/STOP"
exec python3 "$BRO/tools/broccoli_infinite_dev_loop.py"
