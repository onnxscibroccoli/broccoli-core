#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
BROCCOLI_DIR="${BROCCOLI_DIR:-$HOME/broccoli}"
OUT="$BROCCOLI_DIR/window_dump.xml"
R="$BROCCOLI_DIR/rish.sh"
dump() {
  if [[ -x "$R" ]]; then
    sh "$R" sh -c 'uiautomator dump /sdcard/window_dump.xml && cat /sdcard/window_dump.xml' > "$OUT" 2>/dev/null || true
  fi
  [[ -s "$OUT" ]] || uiautomator dump "$OUT" 2>/dev/null || true
}
dump
