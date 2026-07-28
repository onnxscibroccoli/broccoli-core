#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
R="$B/rish.sh"
SD="/sdcard/broccoli_window_dump.xml"
OUT="$B/window_dump.xml"
"$R" -c "uiautomator dump $SD" >/dev/null 2>&1 || true
sleep 0.35
[ -r "$SD" ] && cp -f "$SD" "$OUT" && grep -q hierarchy "$OUT"
