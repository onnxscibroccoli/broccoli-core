#!/data/data/com.termux/files/usr/bin/bash
# Last Grok chat line from UI dump or grok_last.txt → notification body.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
MSG="${1:-}"
SNIP=""

if [ -x "$HOME/broccoli/tools/phrase_grok_dump.py" ]; then
  bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || true
  SNIP="$(python3 "$HOME/broccoli/tools/phrase_grok_dump.py" last "$MSG" 2>/dev/null | head -c 220 || true)"
fi
if [ -z "$SNIP" ] && [ -f "$HOME/broccoli/thread/grok_last.txt" ]; then
  SNIP="$(tail -1 "$HOME/broccoli/thread/grok_last.txt" | head -c 220)"
fi
if [ -z "$SNIP" ]; then
  SNIP="(no reply phrased yet — check Grok FG / dump)"
fi

bash "$HOME/broccoli/lib/notify.sh" "Broccoli · chat" "$SNIP" 0
echo "$SNIP"
