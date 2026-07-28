#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BROCCOLI_DIR="${BROCCOLI_DIR:-$HOME/broccoli}"
STATE="$BROCCOLI_DIR/state.json"
[[ -f "$STATE" ]] || echo '{"task":"","phase":"init","lessons_learned":[],"do_not_repeat":[]}' > "$STATE"
