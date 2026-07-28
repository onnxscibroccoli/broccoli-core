#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
OUT="$B/reports/FS_DISCOVERY.md"
TS="$(date -Iseconds)"
{
  echo "# Filesystem discovery"
  echo "Generated: $TS"
  echo ""
  echo "## Environment"
  echo "- HOME=$HOME"
  echo "- USER=$(whoami 2>/dev/null || echo ?)"
  echo "- PWD=$(pwd)"
  echo "- PATH=$PATH"
  echo ""
  echo "## Termux prefixes"
  for d in /data/data/com.termux/files/usr /data/data/com.termux/files/home "$HOME"; do
    [ -d "$d" ] && echo "- $d ($(du -sh "$d" 2>/dev/null | awk '{print $1}'))"
  done
  echo ""
  echo "## Home top-level"
  ls -la "$HOME" 2>/dev/null || true
  echo ""
  echo "## broccoli tree (depth 4, dirs + key files)"
  if command -v find >/dev/null; then
    find "$B" -maxdepth 4 \( -type d -o -name '*.sh' -o -name '*.md' -o -name '*.json' \) 2>/dev/null | head -400
  fi
  echo ""
  echo "## Storage symlinks (if any)"
  ls -la "$HOME/storage" 2>/dev/null || echo "(no storage — run termux-setup-storage if needed)"
  for s in shared downloads dcim; do
    [ -d "$HOME/storage/$s" ] && echo "### storage/$s" && ls "$HOME/storage/$s" 2>/dev/null | head -30
  done
  echo ""
  echo "## Binaries (automation stack)"
  for c in bash python3 git curl jq rsync tar gzip ssh adb scrcpy rish termux-clipboard-get termux-toast termux-notification termux-open-url; do
    command -v "$c" >/dev/null 2>&1 && echo "- $c -> $(command -v "$c")" || echo "- $c (missing)"
  done
  echo ""
  echo "## Installed packages (head)"
  pkg list-installed 2>/dev/null | head -80 || true
  echo ""
  echo "## Running broccoli/copilot"
  pgrep -af 'broccoli|grok_copilot|agent_' 2>/dev/null || echo "(none)"
  echo ""
  echo "## Disk"
  df -h "$HOME" 2>/dev/null || true
} > "$OUT"
echo "wrote $OUT ($(wc -c < "$OUT") bytes)"
