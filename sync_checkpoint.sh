#!/data/data/com.termux/files/usr/bin/bash
set -e

ROOT="$HOME/broccoli-core"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")

cd "$ROOT"

echo "=== Broccoli Core Sync Checkpoint ==="
echo "Time: $TIMESTAMP"
echo "Branch: $(git branch --show-current)"

mkdir -p tools/sync_history

git status --short > "tools/sync_history/git_status_$TIMESTAMP.txt"

echo "Running compile verification..."
PYTHONPATH="$ROOT" python3 -m compileall runtime >/dev/null

echo "Compile PASS"

git add -A

if git diff --cached --quiet; then
    echo "No Git changes detected."
else
    git commit -m "Broccoli Core checkpoint $TIMESTAMP"
fi

BRANCH=$(git branch --show-current)

echo "Pushing branch: $BRANCH"

git push origin "$BRANCH" || {
    echo "Git push failed - preserving local checkpoint"
}

if command -v rclone >/dev/null; then
    echo "Checking Google Drive..."

    if rclone listremotes | grep -q "^gdrive:"; then

        mkdir -p "$HOME/drive-mirror"

        echo "Syncing Drive mirror..."

        rclone sync \
            gdrive: \
            "$HOME/drive-mirror" \
            --create-empty-src-dirs

        echo "Drive mirror updated"

    else
        echo "No gdrive remote configured - skipping Drive sync"
    fi
else
    echo "rclone unavailable - skipping Drive sync"
fi

git log -5 --oneline

echo "=== CHECKPOINT COMPLETE ==="
