#!/usr/bin/env bash
# broccoli_full_ready.sh — One entry: wait disk → offload redundant → init agent → pull/push chat → optional wire.
set -euo pipefail

HOME="${HOME:-/data/data/com.termux/files/home}"
B="${BROCCOLI_ROOT:-$HOME/broccoli}"
ENVF="$B/meta/full_ready.env"
CONF="$B/meta/drive_offload.conf"
LOG="$B/reports/full_ready.log"
MANIFEST="$B/reports/drive_offload_manifest.jsonl"
STAGING="$B/meta/vault/drive_staging"
META="$B/meta"
THREAD="$B/thread"
QUEUE="$B/queue"

# defaults
MAX_USED_PCT=92
MIN_FREE_KB=1048576
POLL_SEC=30
MAX_WAIT_SEC=7200
KEEP_NEWEST_VERSIONS=2
ARCHIVE_LOGS_OVER_MB=50
DELETE_AFTER_UPLOAD=1
RCLONE_REMOTE="gdrive:Broccoli/offload"
DRIVE_COPY_ROOT=""
RUN_REINIT=0
WIRE_AFTER_PUSH=1
DELIVER_MAC=0
RUN_DISK_CLEAN=1
DRY_RUN=0
SKIP_OFFLOAD=0
SKIP_SYNC=0
PUSH_PROMPT=""

log() { echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

load_env() {
  [[ -f "$ENVF" ]] && set -a && source "$ENVF" && set +a
  [[ -n "${1:-}" ]] && eval "$(echo "$1" | tr ',' '\n' | grep -E '^[A-Z_]+=' || true)" 2>/dev/null || true
}

df_line() { df -k /data 2>/dev/null | tail -1 || df -k . | tail -1; }
used_pct() { df_line | awk '{gsub(/%/,"",$5); print $5}'; }
avail_kb() { df_line | awk '{print $4}'; }

disk_ok() {
  local u a
  u="$(used_pct)"; a="$(avail_kb)"
  [[ -n "$u" && -n "$a" ]] || return 1
  [[ "$u" -lt "$MAX_USED_PCT" && "$a" -ge "$MIN_FREE_KB" ]]
}

wait_disk() {
  local start=0 elapsed u a mb
  start=$(date +%s)
  while ! disk_ok; do
    u="$(used_pct)"; a="$(avail_kb)"; mb=$((a/1024))
    log "WAIT disk used=${u}% free=${mb}MB need used<${MAX_USED_PCT}% free>=$((MIN_FREE_KB/1024))MB"
    if [[ "$RUN_DISK_CLEAN" == "1" && -x "$B/tools/termux_disk_clean.sh" ]]; then
      bash "$B/tools/termux_disk_clean.sh" >>"$LOG" 2>&1 || true
    fi
    if [[ "$SKIP_OFFLOAD" != "1" ]]; then
      offload_phase || true
    fi
    if [[ "$MAX_WAIT_SEC" -gt 0 ]]; then
      elapsed=$(($(date +%s)-start))
      [[ "$elapsed" -lt "$MAX_WAIT_SEC" ]] || { log "FAIL disk timeout"; return 2; }
    fi
    sleep "$POLL_SEC"
  done
  log "OK disk used=$(used_pct)% free=$(($(avail_kb)/1024))MB"
}

have_rclone() {
  command -v rclone >/dev/null 2>&1 && rclone listremotes 2>/dev/null | grep -q .
}

resolve_drive_dir() {
  if [[ -n "$DRIVE_COPY_ROOT" ]]; then
    mkdir -p "$DRIVE_COPY_ROOT" 2>/dev/null && echo "$DRIVE_COPY_ROOT" && return 0
  fi
  for d in \
    "$HOME/storage/shared/Google Drive/Broccoli/offload" \
    "/storage/emulated/0/Google Drive/Broccoli/offload" \
    "/sdcard/Google Drive/Broccoli/offload" \
    "$HOME/storage/downloads/Broccoli_offload"; do
    mkdir -p "$d" 2>/dev/null && echo "$d" && return 0
  done
  return 1
}

upload_method() {
  if have_rclone; then echo rclone; return; fi
  if resolve_drive_dir >/dev/null 2>&1; then echo copy; return; fi
  echo none
}

sha256_file() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'
  elif command -v openssl >/dev/null 2>&1; then openssl dgst -sha256 "$1" | awk '{print $2}'
  else stat -c '%s' "$1"; fi
}

upload_file() {
  local src="$1" base method dest
  base="$(basename "$src")"
  method="$(upload_method)"
  [[ "$DRY_RUN" == "1" ]] && { log "DRY upload $src ($method)"; return 0; }
  case "$method" in
    rclone)
      log "UPLOAD rclone $base"
      rclone copyto "$src" "$RCLONE_REMOTE/$base" --checksum 2>>"$LOG" || return 1
      rclone lsf "$RCLONE_REMOTE/$base" >/dev/null 2>&1 || return 1
      echo "{\"ts\":\"$(date -Iseconds)\",\"method\":\"rclone\",\"src\":\"${src#$HOME/}\",\"dest\":\"$RCLONE_REMOTE/$base\"}" >>"$MANIFEST"
      ;;
    copy)
      dest="$(resolve_drive_dir)/$base"
      log "UPLOAD copy -> $dest"
      cp -f "$src" "$dest" || return 1
      [[ "$(stat -c '%s' "$src")" == "$(stat -c '%s' "$dest")" ]] || return 1
      echo "{\"ts\":\"$(date -Iseconds)\",\"method\":\"copy\",\"src\":\"${src#$HOME/}\",\"dest\":\"$dest\"}" >>"$MANIFEST"
      ;;
    none)
      log "SKIP upload (no rclone/DRIVE_COPY_ROOT): $src"
      return 1
      ;;
  esac
  return 0
}

delete_if_uploaded() {
  local src="$1"
  [[ "$DELETE_AFTER_UPLOAD" != "1" ]] && return 0
  [[ "$DRY_RUN" == "1" ]] && { log "DRY rm $src"; return 0; }
  rm -f "$src" && log "DELETED $src"
}

list_old_versions() {
  local dir="$HOME/broccoli/versions" keep="$KEEP_NEWEST_VERSIONS"
  [[ -d "$dir" ]] || return 0
  ls -1t "$dir"/*.tar.gz "$dir"/*.tgz "$dir"/*.zip 2>/dev/null | awk -v k="$keep" 'NR>k'
}

list_conf_paths() {
  [[ -f "$CONF" ]] || return 0
  while IFS= read -r line; do
    line="${line%%#*}"; line="$(echo "$line" | xargs 2>/dev/null || true)"
    [[ -z "$line" || "$line" == KEEP_* || "$line" == ARCHIVE_* ]] && continue
    [[ "$line" == broccoli/versions/* ]] && continue
    for f in "$HOME"/$line; do [[ -f "$f" ]] && echo "$f"; done
  done <"$CONF"
}

offload_one() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  log "OFFLOAD candidate $f"
  upload_file "$f" && delete_if_uploaded "$f"
}

offload_logs_bundle() {
  local rep="$B/reports" total arc
  [[ -d "$rep" ]] || return 0
  total="$(du -sm "$rep" 2>/dev/null | awk '{print $1}')"
  [[ "${total:-0}" -ge "$ARCHIVE_LOGS_OVER_MB" ]] || return 0
  mkdir -p "$STAGING"
  arc="$STAGING/logs_$(date +%Y%m%d_%H%M%S).tar.gz"
  log "OFFLOAD fat logs ${total}MB -> $arc"
  [[ "$DRY_RUN" == "1" ]] && return 0
  tar -czf "$arc" -C "$B" reports 2>>"$LOG" || return 1
  upload_file "$arc" && delete_if_uploaded "$arc"
  find "$rep" -name '*.log' -type f -exec truncate -s 0 {} \; 2>/dev/null || true
  log "TRUNCATED reports/*.log"
}

offload_phase() { bash "$B/tools/broccoli_offload_mem.sh" run >>"$LOG" 2>&1 || true; }
offload_phase_orig() {
  log "=== offload phase method=$(upload_method) ==="
  local f
  while IFS= read -r f; do [[ -n "$f" ]] && offload_one "$f" || true; done < <(list_old_versions)
  while IFS= read -r f; do [[ -n "$f" ]] && offload_one "$f" || true; done < <(list_conf_paths)
  offload_logs_bundle || true
}

agent_init() {
  log "=== agent init ==="
  rm -f "$META/AGENT_STOP" "$META/HEAL_STOP" "$META/WIRE_STOP"
  [[ -x "$B/tools/go_install.sh" ]] && bash "$B/tools/go_install.sh" >>"$LOG" 2>&1 || true
  [[ -x "$B/tools/agent_ensure_running.sh" ]] && bash "$B/tools/agent_ensure_running.sh" >>"$LOG" 2>&1 || true
  if [[ "$RUN_REINIT" == "1" && -x "$B/tools/reinit_agent.sh" ]]; then
    bash "$B/tools/reinit_agent.sh" >>"$LOG" 2>&1 || true
  fi
  [[ -x "$B/tools/notify_persistent_agent.sh" ]] && bash "$B/tools/notify_persistent_agent.sh" >>"$LOG" 2>&1 || true
}

pull_chat() {
  log "=== pull chat ==="
  mkdir -p "$THREAD" "$B/ui"
  if [[ -x "$B/lib/ui_dump_rish.sh" ]]; then bash "$B/lib/ui_dump_rish.sh" >>"$LOG" 2>&1 || true
  elif command -v brocc >/dev/null; then brocc dump >>"$LOG" 2>&1 || true; fi
  local last="" fp=""
  if [[ -x "$B/tools/phrase_grok_dump.py" ]]; then
    fp="$(python3 "$B/tools/phrase_grok_dump.py" fp 2>/dev/null || true)"
    last="$(python3 "$B/tools/phrase_grok_dump.py" last 2>/dev/null || true)"
    if [[ -n "$last" ]]; then
      echo "$last" >> "$THREAD/grok_last.txt"
      echo "$last" > "$META/last_pulled_reply.txt"
      [[ -n "$fp" ]] && echo "$fp" > "$META/last_pulled_fp"
      printf '\n## Pulled %s\n%s\n' "$(date -Iseconds)" "$last" >> "$THREAD/conversation.md"
    fi
  fi
  [[ -x "$B/tools/ui_dump_chat.py" ]] && python3 "$B/tools/ui_dump_chat.py" lines 2>/dev/null | tail -30 >> "$THREAD/to_chat.md" || true
}

push_chat() {
  log "=== push chat ==="
  mkdir -p "$QUEUE"
  local prompt="$PUSH_PROMPT"
  [[ -z "$prompt" && -f "$META/next_wire_prompt.txt" ]] && prompt="$(head -c 2000 "$META/next_wire_prompt.txt")"
  [[ -z "$prompt" && -s "$QUEUE/pending.txt" ]] && prompt="$(head -1 "$QUEUE/pending.txt" | sed 's/^ASK|//')"
  [[ -z "$prompt" ]] && prompt="Broccoli agent: disk+offload+sync OK. Reply one short ASK line for next wire step."
  printf '%s\n' "ASK|${prompt}" > "$QUEUE/pending.txt"
  printf '\n## Push %s\nASK|%s\n' "$(date -Iseconds)" "$prompt" >> "$THREAD/to_chat.md"
  [[ -x "$B/tools/prepare_mac_bundle.sh" ]] && bash "$B/tools/prepare_mac_bundle.sh" >>"$LOG" 2>&1 || true
  [[ "$DELIVER_MAC" == "1" && -x "$B/tools/deliver_to_mac.sh" ]] && bash "$B/tools/deliver_to_mac.sh" >>"$LOG" 2>&1 || true
  if [[ "$WIRE_AFTER_PUSH" == "1" && -x "$B/tools/agent_tick.sh" ]]; then
    if grep -q 'ai.x.grok' "$B/ui/last_ui.xml" 2>/dev/null; then
      bash "$B/tools/agent_tick.sh" >>"$LOG" 2>&1 || log "WARN agent_tick failed (Grok fg?)"
    else
      log "SKIP wire (Grok not in last_ui dump — open Grok chat, re-run: $0 wire)"
    fi
  fi
}

write_default_conf() {
  [[ -f "$CONF" ]] && return 0
  cat > "$CONF" << 'C'
broccoli/versions/*.tar.gz
broccoli/versions/*.tgz
broccoli/versions/*.zip
C
}

status() {
  echo "disk: used=$(used_pct)% free_mb=$(($(avail_kb)/1024)) $(disk_ok && echo OK || echo WAIT)"
  echo "upload: $(upload_method) remote=${RCLONE_REMOTE:-} drive_root=${DRIVE_COPY_ROOT:-}"
  echo "daemons:"; pgrep -af 'agent_daemon|heal_supervisor' || echo "(none)"
  echo "queue:"; head -1 "$QUEUE/pending.txt" 2>/dev/null || echo "(empty)"
}

main() {
  mkdir -p "$B/reports" "$STAGING"
  load_env "${EXTRA_ENV:-}"
  write_default_conf
  log "======== FULL_READY start ========"
  df_line | tee -a "$LOG"

  # 1) If disk bad: wait loop (offload inside loop to free space)
  if ! disk_ok; then
    wait_disk || exit 2
  else
    log "disk already OK"
  fi

  # 2) Offload again when disk OK (catch anything missed)
  if [[ "$SKIP_OFFLOAD" != "1" ]]; then
    offload_phase
    df_line | tee -a "$LOG"
  fi

  # 3) Re-check disk after offload
  if ! disk_ok; then
    log "WARN still tight after offload; continuing agent/sync anyway"
  fi

  # 4) Agent
  agent_init

  # 5) Pull / push
  if [[ "$SKIP_SYNC" != "1" ]]; then
    pull_chat
    push_chat
  fi

  log "======== FULL_READY done ========"
  echo "FULL_READY_OK $(date -Iseconds) disk_used=$(used_pct)% upload=$(upload_method)"
  status
}

case "${1:-run}" in
  status) load_env; write_default_conf; status ;;
  wait) load_env; wait_disk ;;
  offload) load_env; write_default_conf; offload_phase ;;
  init) load_env; agent_init ;;
  pull) load_env; pull_chat ;;
  push) load_env; push_chat ;;
  wire) load_env; WIRE_AFTER_PUSH=1; push_chat ;;
  dry-run) load_env; DRY_RUN=1; write_default_conf; offload_phase ;;
  run|*) main ;;
esac
