#!/data/data/com.termux/files/usr/bin/bash
set -e

cd ~/broccoli

echo "== Project =="
pwd

echo "== Creating required directories =="
mkdir -p reports logs tmp data/harvest

echo "== Disk usage before cleanup =="
df -h

echo "== Cleaning temporary files =="
find . -type f \( \
    -name "*.tmp" -o \
    -name "*.log.old" -o \
    -name "*.pyc" \
\) -delete 2>/dev/null || true

find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "== Verifying Python import =="
python3 - <<'PY'
try:
    from modules.chat_store import harvest_payload
    print("✓ harvest_payload import OK")
except Exception as e:
    print("✗ Import failed:", e)
PY

echo "== Verifying Google Drive =="
rclone about gdrive: || true

echo "== Creating snapshot =="
{
echo "Broccoli Snapshot"
date
echo
pwd
echo
df -h
echo
ls -la
echo
[ -f chat_loop.log ] && cat chat_loop.log
} > broccoli_snapshot.txt

echo "== Uploading snapshot =="
rclone copy broccoli_snapshot.txt gdrive:BroccoliWorkspaceBackup/ --progress

echo
echo "== Final disk usage =="
df -h

echo
echo "Done."
