#!/usr/bin/env bash
# Upload redundant copies: compress-in-RAM (or stream as-is if already compressed). NO delete unless USER_CONFIRMED_DELETE=1 AND DELETE_AFTER_UPLOAD=1.
set -euo pipefail
B="${BROCCOLI_ROOT:-$HOME/broccoli}"
ENVF="$B/meta/full_ready.env"
CONF="$B/meta/drive_offload.conf"
LOG="$B/reports/drive_offload.log"
MANIFEST="$B/reports/drive_offload_manifest.jsonl"
KEEP="${KEEP_NEWEST_VERSIONS:-2}"
DELETE_AFTER_UPLOAD="${DELETE_AFTER_UPLOAD:-0}"
USER_CONFIRMED_DELETE="${USER_CONFIRMED_DELETE:-0}"

[[ -f "$ENVF" ]] && set -a && source "$ENVF" && set +a

log() { echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

list_old_versions() {
  local dir="$HOME/broccoli/versions"
  [[ -d "$dir" ]] || return 0
  ls -1t "$dir"/*.tar.gz "$dir"/*.tgz "$dir"/*.zip 2>/dev/null | awk -v k="$KEEP" 'NR>k'
}

upload_one() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  log "UPLOAD mem $f"
  local line
  line="$(python3 "$B/tools/drive_upload_mem.py" "$f" 2>>"$LOG")" || { log "FAIL $f"; return 1; }
  echo "$line" >>"$MANIFEST"
  log "OK $line"
  if [[ "$DELETE_AFTER_UPLOAD" == "1" && "$USER_CONFIRMED_DELETE" == "1" ]]; then
    rm -f "$f" && log "DELETED (user confirmed) $f"
  else
    log "KEEP local (no user-confirmed delete) $f"
  fi
}

main() {
  mkdir -p "$B/reports"
  log "=== offload_mem start DELETE=$DELETE_AFTER_UPLOAD CONFIRM=$USER_CONFIRMED_DELETE ==="
  local f
  while IFS= read -r f; do [[ -n "$f" ]] && upload_one "$f" || true; done < <(list_old_versions)
  log "=== offload_mem done ==="
}

case "${1:-run}" in
  list) list_old_versions ;;
  run) main ;;
  *) echo "Usage: $0 {list|run}"; exit 1 ;;
esac
