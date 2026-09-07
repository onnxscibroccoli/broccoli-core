#!/data/data/com.termux/files/usr/bin/bash
# Repo-versioned hook. Runs after a successful fast-forward.
set -u
ROOT="${BROCC_ROOT:-$HOME/broccoli-core}"
cd "$ROOT" || exit 1
chmod +x "$ROOT"/bin/* 2>/dev/null || true
mkdir -p "$ROOT/ops/ondevice-inbox" "$ROOT/ops/ondevice-done" "$HOME/.broccoli"
echo "post-sync $(date -Iseconds) $(git rev-parse --short HEAD)"
exit 0
