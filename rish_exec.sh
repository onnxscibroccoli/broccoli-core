#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BROCCOLI_DIR="${BROCCOLI_DIR:-$HOME/broccoli}"
# Usage: rish_exec.sh 'shell command string'
cmd="$1"
"$BROCCOLI_DIR/rish.sh" -c "$cmd"
