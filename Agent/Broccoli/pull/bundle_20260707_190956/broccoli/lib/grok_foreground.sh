#!/data/data/com.termux/files/usr/bin/bash
set -eu
GROK_PKG=ai.x.grok
XML="$HOME/broccoli/ui/last_ui.xml"
grep -q "package=\"$GROK_PKG\"" "$XML" 2>/dev/null && exit 0
exit 1
