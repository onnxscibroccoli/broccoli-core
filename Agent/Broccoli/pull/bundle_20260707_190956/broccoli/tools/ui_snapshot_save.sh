#!/data/data/com.termux/files/usr/bin/bash
set -eu
TAG="${1:-snap}"
H="$HOME/broccoli/ui/history/$(date +%Y%m%d_%H%M%S)_${TAG}.xml"
mkdir -p "$(dirname "$H")"
cp -f "$HOME/broccoli/ui/last_ui.xml" "$H" 2>/dev/null || true
echo "$H"
