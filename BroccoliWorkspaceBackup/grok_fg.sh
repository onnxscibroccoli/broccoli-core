#!/data/data/com.termux/files/usr/bin/bash
B="${BROCCOLI_DIR:-$HOME/broccoli}"
R="$B/rish.sh"
PKG="${GROK_PACKAGE:-ai.x.grok}"
line=$("$R" -c "dumpsys activity activities 2>/dev/null | grep -E topResumedActivity|head -1" 2>/dev/null || true)
echo "$line"
echo "$line" | grep -q "$PKG"
