#!/data/data/com.termux/files/usr/bin/bash

ROOT="$HOME/broccoli-core"
DEST="gdrive:BroccoliCore/backups/latest"

STATE="$ROOT/.drive_sync"
PIDFILE="$STATE/pid"
LOGFILE="$STATE/sync.log"

mkdir -p "$STATE"

if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Drive sync already running PID=$PID"
        exit 0
    fi
fi

echo $$ > "$PIDFILE"

trap 'rm -f "$PIDFILE"' EXIT

while true
do

echo "$(date) Production sync started" >> "$LOGFILE"

rclone sync \
"$ROOT" \
"$DEST" \
--exclude ".git/**" \
--exclude "__pycache__/**" \
--exclude "*.pyc" \
--exclude ".drive_sync/**" \
--exclude "quarantine/**" \
--exclude "_quarantine/**" \
--exclude "reports/**" \
--exclude "Agent/**" \
--exclude "BroccoliWorkspaceBackup/**" \
--exclude "**/.ssh/**" \
--exclude "**/vault/**" \
--exclude "**/*pat*" \
--exclude "**/*token*" \
--exclude "**/*secret*" \
--drive-chunk-size 64M \
--transfers 4 \
--checkers 8 \
--stats 30s \
--stats-one-line \
--log-file "$LOGFILE" \
--log-level INFO

echo "$(date) Sync cycle complete" >> "$LOGFILE"

sleep 600

done
