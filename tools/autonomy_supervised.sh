#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HOME}/broccoli-core"
cd "$ROOT" || exit 1
N="${1:-120}"
export PYTHONPATH="$ROOT"
bash tools/repository_health.sh >/dev/null || true
bash tools/drive_sync_heartbeat.sh
bash tools/rotate_processed_events.sh 50
timeout -s INT "$N" python3 -u -m runtime.main || true
bash tools/drive_sync_heartbeat.sh
bash tools/rotate_processed_events.sh 50
df -h . | tail -1
