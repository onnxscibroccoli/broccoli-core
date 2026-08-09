#!/data/data/com.termux/files/usr/bin/bash
# Continuous always-on loop (15s cadence). Ctrl+C or broccoli_always_on_stop.sh to exit.
set -euo pipefail
ROOT="${HOME}/broccoli-core"
META="${ROOT}/meta/always_on"
mkdir -p "$META"
echo $$ >"$META/supervisor.pid"
INTERVAL="${1:-15}"
cd "$ROOT" || exit 1
while true; do
  bash tools/broccoli_always_on.sh || true
  sleep "$INTERVAL"
done
