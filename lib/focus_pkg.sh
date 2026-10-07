#!/data/data/com.termux/files/usr/bin/bash
PKG="${1:-ai.x.grok}"
RAW="$(printf 'dumpsys activity activities\n' | bash /data/data/com.termux/files/home/broccoli-core/lib/rish_shell.sh 2>/dev/null || true)"
echo "$RAW" | grep -iE 'topResumedActivity|mResumedActivity' | head -2
echo "$RAW" | grep -q "$PKG" && exit 0 || exit 1
