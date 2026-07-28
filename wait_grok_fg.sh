#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
R="$B/rish.sh"
PKG="${GROK_PACKAGE:-ai.x.grok}"
for i in $(seq 1 25); do
  if "$R" -c "dumpsys activity activities 2>/dev/null|grep -E topResumedActivity|head -1" 2>/dev/null|grep -q "$PKG"; then
    echo "fg_ok"
    exit 0
  fi
  sleep 1
done
echo "fg_fail"
exit 1
