#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
R="$B/rish.sh"; PKG="${GROK_PACKAGE:-ai.x.grok}"
SD="/sdcard/broccoli_window_dump.xml"; OUT="$B/window_dump.xml"
if "$R" -c "dumpsys activity activities 2>/dev/null|grep topResumedActivity|head -1" 2>/dev/null|grep -q "$PKG"; then
  "$R" -c "uiautomator dump $SD" 2>/dev/null; sleep 0.3
  [ -r "$SD" ] && cp -f "$SD" "$OUT" && exit 0
fi
bash "$B/ui_grok.sh"
