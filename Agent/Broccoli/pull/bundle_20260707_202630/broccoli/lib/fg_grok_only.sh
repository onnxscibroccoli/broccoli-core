#!/data/data/com.termux/files/usr/bin/bash
set -eu
. "$HOME/broccoli/boot/GROK_NATIVE.conf"
for _ in 1 2 3 4 5; do
  bash "$HOME/broccoli/lib/launch_grok_native.sh" >/dev/null 2>&1 || true
  sleep 0.5
  bash "$HOME/broccoli/lib/focus_pkg.sh" "$GROK_PKG" && exit 0
done
exit 1
