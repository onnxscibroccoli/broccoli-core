#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
source "$B/lib/rish_ui.sh"
D=0; ui_dump && D=1 || true
PARSE=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml" 2>/dev/null || echo "null")
printf '{"rish":"%s","clipboard":"%s","dump_ok":%s,"parse":%s}\n' \
  "$(command -v rish)" "$(command -v termux-clipboard-set)" "$D" "$PARSE"
