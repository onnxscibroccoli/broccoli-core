#!/data/data/com.termux/files/usr/bin/bash
set -eu
. "$HOME/broccoli/boot/GROK_NATIVE.conf"
bash "$HOME/broccoli/lib/adb_rish.sh" "am force-stop com.android.chrome" >/dev/null 2>&1 || true
bash "$HOME/broccoli/lib/adb_rish.sh" "am start -n ${GROK_COMPONENT}" >/dev/null 2>&1 || true
