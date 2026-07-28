#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
B="${BROCCOLI_DIR:-$HOME/broccoli}"
bash "$B/preflight.sh" || true
echo "--- Grok foreground dump ---"
bash "$B/ui_grok.sh" && wc -c "$B/window_dump.xml" && grep -c 'ai.x.grok' "$B/window_dump.xml" || true
