#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
LOG="$B/reports/termux_clean.log"
DRY="${1:-dry}"
P="${PREFIX:-/data/data/com.termux/files/usr}"

log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }
run(){
  if [ "$DRY" = "dry" ]; then log "DRY: $*"; return 0; fi
  log "RUN: $*"
  eval "$@"
}

log "=== termux clean mode=$DRY ==="
df -h "$HOME" | tail -1 | tee -a "$LOG"

run "pkg clean -y 2>/dev/null || apt clean 2>/dev/null || true"
run "pip cache purge 2>/dev/null || true"

V="$B/versions"
if [ -d "$V" ]; then
  cnt=$(ls -1 "$V"/*.tar.gz 2>/dev/null | wc -l)
  if [ "$cnt" -gt 2 ]; then
    ls -t "$V"/*.tar.gz 2>/dev/null | tail -n +3 | while read -r f; do
      run "rm -f \"$f\""
    done
  fi
fi

run "rm -rf \"$B/quarantine/staging\"/* 2>/dev/null || true"
for f in "$B"/reports/*.log "$B"/reports/copilot.log; do
  [ -f "$f" ] && [ "$(stat -c%s "$f" 2>/dev/null || echo 0)" -gt 5000000 ] && run ": > \"$f\""
done
find "$B/reports" -name 'ui_dump*.xml' -mtime +1 -delete 2>/dev/null || true

[ -x "$B/tools/disk_rescue.sh" ] && run "bash \"$B/tools/disk_rescue.sh\"" || true

df -h "$HOME" | tail -1 | tee -a "$LOG"
log "=== done ==="
