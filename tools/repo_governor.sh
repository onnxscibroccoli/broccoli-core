#!/data/data/com.termux/files/usr/bin/bash

ROOT="$HOME/broccoli-core"
STATE="$ROOT/meta/repo_governor.json"

mkdir -p "$ROOT/meta"

while true; do
    cd "$ROOT" || exit 1

    BRANCH=$(git branch --show-current 2>/dev/null)
    STATUS=$(git status --porcelain | wc -l)
    AHEAD=$(git rev-list --left-right --count origin/$BRANCH...HEAD 2>/dev/null | awk '{print $2}')
    DISK=$(df -h . | awk 'NR==2{print $5}')
    TIME=$(date +%s)

    cat > "$STATE" <<JSON
{
  "timestamp": $TIME,
  "branch": "$BRANCH",
  "ahead": $AHEAD,
  "changes": $STATUS,
  "disk_used": "$DISK"
}
JSON

    echo "[RepoGovernor] branch=$BRANCH ahead=$AHEAD changes=$STATUS disk=$DISK"

    sleep 60
done
