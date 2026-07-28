#!/data/data/com.termux/files/usr/bin/bash
set -e
B="$HOME/broccoli"
[ -s "$B/queue/agent_task.txt" ] || exit 1
[ -f "$B/reports/ui_dump.xml" ] || exit 1
python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml" | python3 -c \
  "import sys,json; d=json.load(sys.stdin); raise SystemExit(0 if d.get('ok') else 1)"
