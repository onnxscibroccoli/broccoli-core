#!/data/data/com.termux/files/usr/bin/bash
# Known-good fallback wire: short msg, ENTER-first, Grok FG, phrase receive.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
MSG="${1:-Reply exactly one word: HEAL_OK}"
LOG="$HOME/broccoli/reports/heal_wire.log"
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }
export HEAL_FALLBACK=1
log "fallback send: $MSG"
bash "$HOME/broccoli/lib/fg_grok_only.sh" >/dev/null 2>&1 || bash "$HOME/broccoli/lib/launch_grok_native.sh" >/dev/null 2>&1 || true
bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || true
[ -x "$HOME/broccoli/tools/dump_send_row.sh" ] && bash "$HOME/broccoli/tools/dump_send_row.sh" >/dev/null 2>&1 || true

if [ -x "$HOME/broccoli/tools/wire_send_ui.sh" ]; then
  REPLY="$(bash "$HOME/broccoli/tools/wire_send_ui.sh" "$MSG" 2>>"$LOG")" && { log "ok $REPLY"; echo "$REPLY"; exit 0; }
fi
log "fallback fail"
exit 1
