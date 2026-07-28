#!/data/data/com.termux/files/usr/bin/bash
set -e
B="$HOME/broccoli"
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$B/reports/wire_send.log"
P="${1:-}"; [ -n "$P" ] || exit 1
source "$B/meta/wire_coords.env"
source "$B/lib/rish_ui.sh"
log() { echo "$(date -Iseconds) $*" >>"$LOG"; }
log "SEND len=${#P}"
command -v rish >/dev/null || { log ERR_no_rish; exit 1; }
grep -qi "$GROK_PKG" "$B/reports/ui_dump.xml" 2>/dev/null || { open_grok; sleep 1.2; }
ui_dump >>"$LOG" 2>&1 || { log dump_fail; exit 1; }
J=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
log "$J"
OK=$(echo "$J" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))")
if [ "$OK" != "True" ]; then
  tap "$COMPOSER_X" "$COMPOSER_Y"; sleep 0.35
  ui_dump >>"$LOG" 2>&1 || true
  J=$(python3 "$B/tools/parse_grok_ui.py" "$B/reports/ui_dump.xml")
  OK=$(echo "$J" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok'))")
fi
[ "$OK" = "True" ] || { log no_composer; exit 1; }
CX=$(echo "$J" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['composer']['x'])")
CY=$(echo "$J" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['composer']['y'])")
tap "$CX" "$CY"
command -v termux-clipboard-set >/dev/null && termux-clipboard-set "$P" >>"$LOG" 2>&1 || true
keyev 279; sleep 0.25
SX=$(echo "$J" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('send'); print(s['x'] if s else '')" 2>/dev/null || true)
SY=$(echo "$J" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('send'); print(s['y'] if s else '')" 2>/dev/null || true)
if [ -n "$SX" ]; then tap "$SX" "$SY"; else tap "$SEND_X" "$SEND_Y"; fi
date +%s > "$B/meta/last_wire_ts"
log send_ok
