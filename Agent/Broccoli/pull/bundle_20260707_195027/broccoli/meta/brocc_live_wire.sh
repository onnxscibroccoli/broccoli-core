#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
META="$HOME/broccoli/meta"
IN="$META/inbox/from_mac"
LOG="$META/live_wire.log"
CLIP_HASH="$META/.clip_hash"
PY=python3

log() { echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

run_grok_block() {
  local f="$1"
  log "live_wire run $f"
  "$PY" "$META/brocc_state.py" set_phase running 2>/dev/null || \
    "$PY" -c "import brocc_state" 2>/dev/null || true
  # Only lines that look like brocc commands (safety)
  grep -E '^(\s*#|python3 |~/|bash |termux-|pkg |rish )' "$f" | grep -v '^#' > "$META/.grok_exec.sh" || true
  if [[ -s "$META/.grok_exec.sh" ]]; then
    bash "$META/.grok_exec.sh" >>"$LOG" 2>&1 || log "exec had errors (continuing)"
  fi
  mv -f "$f" "${f}.done"
  "$PY" - <<'PY'
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("brocc_state", Path.home()/"broccoli/meta/brocc_state.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
m.set_phase("await_grok")
PY
  "$META/brocc_loop_emit.sh" force
}

# 1) Inbox files (Mac rish push) — highest priority
for f in "$IN"/grok_commands.sh "$IN"/grok_reply.txt; do
  [[ -f "$f" ]] || continue
  [[ -f "${f}.done" ]] && continue
  if [[ "$f" == *grok_reply.txt ]]; then
    # wrap loose text as comments + allow embedded lines
    {
      echo "# grok_reply"
      cat "$f"
    } > "$IN/grok_commands.from_reply.sh"
    run_grok_block "$IN/grok_commands.from_reply.sh"
  else
    run_grok_block "$f"
  fi
done

# 2) Optional clipboard wire (continuous prompting on phone)
if [[ "${LIVE_WIRE_CLIP:-0}" == "1" ]] && command -v termux-clipboard-get >/dev/null; then
  clip="$(termux-clipboard-get 2>/dev/null || true)"
  if [[ -n "$clip" ]]; then
    hash="$(printf '%s' "$clip" | sha256sum | awk '{print $1}')"
    if [[ -f "$CLIP_HASH" ]] && [[ "$(cat "$CLIP_HASH")" == "$hash" ]]; then
      : # same clip, skip
    else
      echo "$hash" > "$CLIP_HASH"
      # Only accept if marker present (avoid random copies)
      if printf '%s' "$clip" | grep -q '^BROCC_GROK:'; then
        printf '%s\n' "$clip" | sed '1s/^BROCC_GROK://' > "$IN/grok_commands.from_clip.sh"
        run_grok_block "$IN/grok_commands.from_clip.sh"
      fi
    fi
  fi
fi
