#!/data/data/com.termux/files/usr/bin/bash
# On failure: investigate + gap + calibrate send row (research on device).
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/heal_research.log"
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }
log "research start"
[ -x "$HOME/broccoli/tools/investigate_system.sh" ] && bash "$HOME/broccoli/tools/investigate_system.sh" --live >>"$LOG" 2>&1 || true
[ -x "$HOME/broccoli/lib/fg_grok_only.sh" ] && bash "$HOME/broccoli/lib/fg_grok_only.sh" >>"$LOG" 2>&1 || true
[ -x "$HOME/broccoli/tools/dump_send_row.sh" ] && bash "$HOME/broccoli/tools/dump_send_row.sh" >>"$LOG" 2>&1 || true
[ -x "$HOME/broccoli/tools/gap_watch.sh" ] && bash "$HOME/broccoli/tools/gap_watch.sh" "heal" >>"$LOG" 2>&1 || true
log "research done"
