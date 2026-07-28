#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BROCCOLI_DIR="${BROCCOLI_DIR:-$HOME/broccoli}"
exec sh "$BROCCOLI_DIR/rish.sh" sh -c "$*"
