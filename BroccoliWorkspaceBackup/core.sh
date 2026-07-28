#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BROCCOLI_DIR="${BROCCOLI_DIR:-$HOME/broccoli}"
export BROCCOLI_DIR
exec python3 "$BROCCOLI_DIR/broccoli_chat_loop.py" "$@"
