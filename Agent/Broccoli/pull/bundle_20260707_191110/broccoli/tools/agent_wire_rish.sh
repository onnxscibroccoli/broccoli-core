#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
PROMPT="$(bash "$B/tools/wire_build_prompt.sh" "${1:-wire_ok}")"
bash "$B/tools/notify_toast.sh" "Wire" "rish…" broccoli_wire
REPLY="$(bash "$B/tools/wire_send_ui.sh" "$PROMPT" 2>>"$B/reports/wire_send.log" || true)"
[ -n "$REPLY" ] && printf '%s\n' "$REPLY" >> "$B/thread/grok_last.txt"
bash "$B/lib/ui_dump_rish.sh" 2>/dev/null || true
bash "$B/tools/prepare_mac_bundle_redacted.sh"
bash "$B/tools/notify_toast.sh" "Wire" "done" broccoli_wire
