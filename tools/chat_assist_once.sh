#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HOME}/broccoli-core"
cd "$ROOT" || exit 1
export PYTHONPATH="$ROOT"
APP="${1:-grok}"
MODE="${2:-open}"
if [ "$MODE" = "open-send" ]; then
  python3 -m runtime.autonomy.chat_assist --app "$APP" --open --auto-reply
else
  python3 -m runtime.autonomy.chat_assist --app "$APP" --open
fi
