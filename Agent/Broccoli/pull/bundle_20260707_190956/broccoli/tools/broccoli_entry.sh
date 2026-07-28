#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
B="$HOME/broccoli"
prepare_mac_bundle(){
  OUT="$B/reports/DEVICE_OUTPUT_FOR_MAC.txt"
  PKG=""
  [ -f "$B/reports/ui_dump.xml" ] && PKG="$(grep -o 'package="[^"]*"' "$B/reports/ui_dump.xml" | head -1 || true)"
  {
    echo "===== BROCCOLI DEVICE OUTPUT $(date -Iseconds) ====="
    echo "## DAEMONS"; pgrep -af 'agent_daemon|heal_supervisor' 2>/dev/null || true
    echo ""; echo "## QUEUE"; cat "$B/queue/pending.txt" 2>/dev/null || true
    echo ""; echo "## AGENT_ITERATION"; cat "$B/meta/agent_iteration.json" 2>/dev/null || true
    echo ""; echo "## GROK_LAST"; tail -8 "$B/thread/grok_last.txt" 2>/dev/null || true
    echo ""; echo "## DUMP_PKG"; echo "${PKG:-no_dump}"
    echo ""; echo "## WIRE_LOG"; tail -25 "$B/reports/wire_send.log" 2>/dev/null || true
    echo ""; echo "## AGENT_TICK"; tail -12 "$B/reports/agent_tick.log" 2>/dev/null || true
    echo "===== END ====="
  } > "$OUT"
}
deliver_mac(){
  prepare_mac_bundle
  BODY="$(head -c 3800 "$B/reports/DEVICE_OUTPUT_FOR_MAC.txt")"
  { echo ""; echo "--- DEVICE_OUTPUT $(date -Iseconds) ---"; cat "$B/reports/DEVICE_OUTPUT_FOR_MAC.txt"; echo "---"; } >> "$B/thread/to_chat.md"
  command -v termux-clipboard-set >/dev/null 2>&1 && termux-clipboard-set <<< "$BODY" || true
  echo "===== PASTE TO MAC GROK ====="
  head -c 4000 "$B/reports/DEVICE_OUTPUT_FOR_MAC.txt"
  echo ""; echo "===== END ====="
}
cmd_wire(){
  P="${1:-Reply exactly one word: WIRE_OK}"
  REPLY="$(bash "$B/tools/wire_send_ui.sh" "$P" 2>>"$B/reports/wire_send.log" || true)"
  echo "reply=${REPLY:-empty}"
  [ -n "$REPLY" ] && printf '%s\n' "$REPLY" >> "$B/thread/grok_last.txt"
  bash "$B/lib/ui_dump_rish.sh" >/dev/null 2>&1 || true
  grep -o 'package="[^"]*"' "$B/reports/ui_dump.xml" 2>/dev/null | sort -u | head -5 || true
  [ -x "$B/tools/agent_consume_iteration.sh" ] && bash "$B/tools/agent_consume_iteration.sh" "$P" "${REPLY:-}" >>"$B/reports/agent_consume.log" 2>&1 || true
  deliver_mac
}
case "${1:-help}" in
  wire) shift; cmd_wire "$@" ;;
  pull) deliver_mac ;;
  status) prepare_mac_bundle; head -35 "$B/reports/DEVICE_OUTPUT_FOR_MAC.txt" ;;
  *) echo "broccoli_entry.sh wire|pull|status";;
esac
