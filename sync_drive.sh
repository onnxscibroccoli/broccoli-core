#!/data/data/com.termux/files/usr/bin/bash
set -e

cd ~/broccoli-core

echo "========================================"
echo " Broccoli Incremental Drive Sync"
echo "========================================"

mkdir -p tools
mkdir -p .sync_stage

python3 tools/drive_sync.py
