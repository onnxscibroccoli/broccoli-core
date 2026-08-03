#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HOME}/broccoli-core"
cd "$ROOT"||exit 1
export PYTHONPATH="$ROOT"
CMD="${1:-status}"; shift || true
python3 -m runtime.autonomy.dev_round "\( CMD" " \)@"
