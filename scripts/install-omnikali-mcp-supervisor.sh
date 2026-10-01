#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="${BROCCOLI_ROOT:-$HOME/broccoli-core}"
SRC="$ROOT/bin/omnikali-mcp-supervisor"
DST="$HOME/bin/omnikali-mcp-supervisor"
BOOT="$HOME/.termux/boot/broccoli-supervisor"
install -d -m 700 "$HOME/bin" "$HOME/.termux/boot"
install -m 700 "$SRC" "$DST"
if ! grep -Fq 'omnikali-mcp-supervisor' "$BOOT"; then
  sed -i '/^exec "\$SUPERVISOR"$/i if [ -x "$HOME/bin/omnikali-mcp-supervisor" ]; then nohup "$HOME/bin/omnikali-mcp-supervisor" >/dev/null 2>&1 & fi' "$BOOT"
fi
printf '%s\n' "MCP supervisor installed: $DST"
