#!/data/data/com.termux/files/usr/bin/bash
set -u
export BRO="${BRO:-$HOME/broccoli}"
export PYTHONPATH="$BRO/lib"
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
export BROCCOLI_GROK_PKG="${BROCCOLI_GROK_PKG:-ai.x.grok}"
python3 "$BRO/tools/heal_debug_all.py"
