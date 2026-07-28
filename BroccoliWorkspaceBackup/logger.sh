#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BROCCOLI_DIR="${BROCCOLI_DIR:-$HOME/broccoli}"
echo "[$(date -Iseconds)] $*" >> "$BROCCOLI_DIR/error.log"
