#!/data/data/com.termux/files/usr/bin/bash
set -e

REPORT="$HOME/broccoli/storage_report.txt"

{
echo "========== Broccoli Storage Audit =========="
date
echo

echo "Filesystem:"
df -h /data
echo

echo "Top of HOME:"
du -xh "$HOME" --max-depth=2 2>/dev/null | sort -h | tail -40
echo

echo "Top of /data/data:"
du -xh /data/data --max-depth=1 2>/dev/null | sort -h
echo

echo "Largest files in HOME:"
find "$HOME" -type f -printf '%s %p\n' 2>/dev/null | sort -nr | head -30
echo

echo "Cleaning old caches..."

find ~/broccoli/logs -type f -size +10M -exec gzip -f {} \; 2>/dev/null || true
find ~/broccoli/data/harvest -type f -mtime +7 -delete 2>/dev/null || true
find ~/broccoli/reports -type f -mtime +14 -delete 2>/dev/null || true

rm -rf ~/.cache/* 2>/dev/null || true
find "$HOME" -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$HOME" -name "*.pyc" -delete 2>/dev/null || true

echo
echo "Filesystem after cleanup:"
df -h /data
} | tee "$REPORT"

if command -v termux-clipboard-set >/dev/null 2>&1; then
    cat "$REPORT" | termux-clipboard-set
    echo
    echo "✓ Report copied to clipboard."
else
    echo
    echo "termux-clipboard-set not installed."
fi
