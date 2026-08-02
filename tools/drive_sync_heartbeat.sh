#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${HOME}/broccoli-core"
mkdir -p "\( ROOT/.drive_sync"
printf "%s HEARTBEAT drive_sync status=ok note=heartbeat_script\n" " \)(date -Is)" >> "$ROOT/.drive_sync/sync.log"
echo drive_sync heartbeat written
