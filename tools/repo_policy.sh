#!/data/data/com.termux/files/usr/bin/bash

ROOT="$HOME/broccoli-core"

while true; do
    JSON="$ROOT/meta/repo_governor.json"

    [ -f "$JSON" ] || { sleep 5; continue; }

    AHEAD=$(grep '"ahead"' "$JSON" | grep -o '[0-9]\+')
    CHANGES=$(grep '"changes"' "$JSON" | grep -o '[0-9]\+')
    DISK=$(grep '"disk_used"' "$JSON" | grep -o '[0-9]\+')

    if [ "$DISK" -ge 95 ]; then
        echo "$(date) WARNING: Disk ${DISK}% full" >> "$ROOT/reports/repo_policy.log"
    fi

    if [ "$AHEAD" -gt 0 ]; then
        echo "$(date) Repository has unpushed commits" >> "$ROOT/reports/repo_policy.log"
    fi

    if [ "$CHANGES" -gt 10 ]; then
        echo "$(date) Working tree becoming dirty" >> "$ROOT/reports/repo_policy.log"
    fi

    sleep 10
done
