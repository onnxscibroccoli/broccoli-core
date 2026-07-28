#!/data/data/com.termux/files/usr/bin/bash
B="${B:-$HOME/broccoli}"
GROK_PKG="${GROK_PKG:-com.ai.x.grok}"
rish_ok() { command -v rish >/dev/null 2>&1; }
tap() { rish -c "input tap $1 $2"; }
keyev() { rish -c "input keyevent $1"; }
open_grok() {
  rish -c "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p $GROK_PKG" 2>/dev/null || true
}
ui_dump() {
  local OUT="$B/reports/ui_dump.xml" TMP="$B/reports/ui_dump_work.xml"
  rm -f "$TMP" 2>/dev/null || true
  rish_ok || { echo NO_RISH >"$OUT"; return 1; }
  rish -c "uiautomator dump /sdcard/broccoli_ui.xml && cat /sdcard/broccoli_ui.xml" >"$TMP" 2>/dev/null || return 1
  [ -s "$TMP" ] && grep -q hierarchy "$TMP" && mv -f "$TMP" "$OUT"
}
