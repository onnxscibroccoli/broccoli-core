#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home
rclone sync ./broccoli-core gdrive:broccoli-core --verbose --progress --exclude '.git/**' --exclude '__pycache__/**' --exclude '*.log'
echo "✅ Synced at $(date)" >> broccoli-core/sync.log
