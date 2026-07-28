#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
HASH=$(printf '%s' "$PARSE" | sha256sum | awk '{print $1}')
LAST="$B/meta/last_ui_chat.hash"
OLD=$(cat "$LAST" 2>/dev/null || echo "")
printf '%s' "$HASH" > "$LAST"
CT=$(printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('composer_text') or '').strip())")
[ -n "$CT" ] && exit 1
[ "$HASH" = "$OLD" ] && exit 1
[ -s "$B/queue/agent_task.txt" ] && exit 0
printf '%s' "$PARSE" | python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('visible_text') or []; raise SystemExit(0 if t else 1)"
