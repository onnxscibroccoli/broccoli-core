#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
B="${BROCCOLI_DIR:-$HOME/broccoli}"
echo "=== Broccoli preflight (Shizuku + rish) ==="
FAIL=0
if ! "$B/rish.sh" -c 'whoami' 2>/dev/null | grep -q shell; then
  echo "FAIL: rish not running as shell (Shizuku stopped or not exported?)"
  FAIL=1
else
  echo "PASS: whoami=shell"
fi
if ! "$B/rish.sh" -c 'id' 2>/dev/null | grep -q 'uid=2000'; then
  echo "WARN: id may not be uid=2000(shell) — still try dump"
fi
# Dump to shared storage, read from Termux (HackTricks / Shizuku pattern)
SD="/sdcard/broccoli_preflight_dump.xml"
"$B/rish.sh" -c "uiautomator dump '$SD'" 2>/dev/null || true
sleep 0.4
if [[ -r "$SD" ]] && grep -q hierarchy "$SD" 2>/dev/null; then
  echo "PASS: uiautomator dump on /sdcard ($(wc -c <"$SD") bytes)"
else
  echo "FAIL: cannot dump/read $SD (storage permission? run: termux-setup-storage)"
  FAIL=1
fi
exit "$FAIL"
