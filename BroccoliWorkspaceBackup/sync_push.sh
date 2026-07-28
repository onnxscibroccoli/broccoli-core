#!/usr/bin/env bash
set -euo pipefail

B="${BROCCOLI_DIR:-$HOME/broccoli}"
LOG_DIR="$B/logs"
mkdir -p "$LOG_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting Broccoli workspace backup sync..."

# 1. Clean up stale transient footprints to save cloud allocation space
find "$B" -type f -name "*.tmp" -mtime +1 -delete || true
find "$B" -type f -name "window_dump.xml" -mtime +2 -delete || true

# 2. Run your workspace synchronization command safely
# Replace standard `rclone` / `gdrive` hook commands below as required by your runtime environment
if command -v rclone &> /dev/null; then
    rclone sync "$B/" "gdrive:BroccoliWorkspaceBackup" \
        --exclude "logs/**" \
        --exclude "*.tmp" \
        --log-file="$LOG_DIR/sync.log" \
        --log-level INFO
    echo "✅ Backup successfully synced to Google Drive via rclone."
else
    echo "⚠️ rclone binary not detected. Local changes kept safely in $B."
    echo "To configure Drive pushing, run: pkg install rclone && rclone config"
fi
