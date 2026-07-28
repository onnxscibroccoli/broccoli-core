#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
LOG="$B/chat_loop.log"
echo "[$(date)] Efficient sync" >> "$LOG"
find "$B" -name "*.tmp" -delete
find "$B/data/harvest" -type f -mtime +1 -delete || true
if command -v rclone >/dev/null; then
    rclone sync "$B/" "gdrive:BroccoliWorkspaceBackup" \
        --exclude "logs/**" --exclude "data/harvest/**" --exclude "*.tmp" \
        --delete-excluded --fast-list --log-level NOTICE >> "$LOG" 2>&1 || true
fi
df -h . >> "$LOG"
