#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HOME}/broccoli-core"
cd "$ROOT"||exit 1
export PYTHONPATH="$ROOT"
python3 -m runtime.autonomy.aim_ui_dump "${1:-dump}"
