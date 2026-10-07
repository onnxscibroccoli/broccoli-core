#!/data/data/com.termux/files/usr/bin/bash
set -uo pipefail
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
OUT="$HOME/broccoli/ui/last_ui.xml"
TMP="/sdcard/brocc_ui_dump.xml"
mkdir -p "$(dirname "$OUT")"
bash "$HOME/aim_rish_ensure.sh" >/dev/null 2>&1 || true
bash /data/data/com.termux/files/home/broccoli-core/lib/rish_run.sh "uiautomator dump $TMP" 2>/dev/null || bash /data/data/com.termux/files/home/broccoli-core/lib/rish_run.sh "cmd accessibility refresh" 2>/dev/null; bash /data/data/com.termux/files/home/broccoli-core/lib/rish_run.sh "uiautomator dump $TMP"
bash /data/data/com.termux/files/home/broccoli-core/lib/rish_run.sh "cat $TMP" > "$OUT" 2>/dev/null || bash /data/data/com.termux/files/home/broccoli-core/lib/rish_run.sh "cp $TMP /data/data/com.termux/files/home/broccoli/ui/last_ui.xml" 2>/dev/null
if [ -s "$OUT" ]; then
  echo "UI_DUMP ok bytes=$(wc -c <"$OUT") path=$OUT"
else
  echo "UI_DUMP fail"
  exit 1
fi
