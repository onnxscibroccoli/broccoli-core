#!/data/data/com.termux/files/usr/bin/bash
PKG="${1:-ai.x.grok}"
RAW="$(printf 'dumpsys activity activities\n' | rish 2>/dev/null || true)"
echo "$RAW" | grep -iE 'topResumedActivity|mResumedActivity' | head -2
echo "$RAW" | grep -q "$PKG" && exit 0 || exit 1
