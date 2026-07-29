#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
LOG="$HOME/broccoli/reports/agent_apply.log"
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }
python3 "$HOME/broccoli/tools/extract_grok_code.py" >>"$LOG" 2>&1 || true
RUN=0
for f in $(ls -t "$HOME/broccoli/sandbox/from_grok"/block_*.sh 2>/dev/null | head -3); do
  [ -s "$f" ] || continue
  log "run $f"
  bash "$f" >>"$LOG" 2>&1 || log "rc=$? $f"
  RUN=1
done
[ "$RUN" -eq 1 ] && log "applied" || log "no_blocks"
