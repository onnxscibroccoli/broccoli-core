#!/data/data/com.termux/files/usr/bin/bash
# Retired archived launcher; source content below is preserved for provenance.
echo "RETIRED_PHYSICAL_RISH: use broccoli-core/lib/rish_run.sh" >&2
return 78 2>/dev/null || exit 78
set -uo pipefail
export RISH_APPLICATION_ID="${RISH_APPLICATION_ID:-com.termux}"
OUT="$HOME/broccoli/ui/last_ui.xml"
TMP="/sdcard/brocc_ui_dump.xml"
mkdir -p "$(dirname "$OUT")"
bash "$HOME/aim_rish_ensure.sh" >/dev/null 2>&1 || true
rish -c "uiautomator dump $TMP" 2>/dev/null || rish -c "cmd accessibility refresh" 2>/dev/null; rish -c "uiautomator dump $TMP"
rish -c "cat $TMP" > "$OUT" 2>/dev/null || rish -c "cp $TMP /data/data/com.termux/files/home/broccoli/ui/last_ui.xml" 2>/dev/null
if [ -s "$OUT" ]; then
  echo "UI_DUMP ok bytes=$(wc -c <"$OUT") path=$OUT"
else
  echo "UI_DUMP fail"
  exit 1
fi
