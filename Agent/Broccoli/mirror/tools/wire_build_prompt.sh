#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
ID="${1:-wire_ok}"
F="$B/prompts/${ID}.txt"
[ -f "$F" ] || F="$B/prompts/wire_ok.txt"
cat "$F"
