\
#!/data/data/com.termux/files/usr/bin/bash
# Must run before clip/send/pull. Focus existing Grok chat or open new.
set -euo pipefail
BRO="${BRO:-$HOME/broccoli}"
LOG="$BRO/reports/chat_focus.log"
mkdir -p "$BRO/reports"
GROK_PKG="${BROCCOLI_GROK_PKG:-ai.x.grok}"   # adjust after discovery
MODE="${1:-reuse}"   # reuse | new

log() { echo "$(date -Iseconds 2>/dev/null || date) $*" | tee -a "$LOG"; }

# --- 1) Foreground Grok (am start) ---
if command -v am >/dev/null 2>&1; then
  if [[ "$MODE" == "new" ]]; then
    am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n "${GROK_PKG}/.MainActivity" 2>/dev/null \
      || am start -n "${GROK_PKG}/.ui.main.MainActivity" 2>/dev/null \
      || monkey -p "$GROK_PKG" -c android.intent.category.LAUNCHER 1 2>/dev/null || true
    sleep 2
    log "LAUNCH new attempt pkg=$GROK_PKG"
  else
    am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n "${GROK_PKG}/.MainActivity" 2>/dev/null \
      || monkey -p "$GROK_PKG" -c android.intent.category.LAUNCHER 1 2>/dev/null || true
    sleep 1
    log "LAUNCH reuse pkg=$GROK_PKG"
  fi
fi

# --- 2) Prefer project Rish UI (if implemented) ---
PY_HOOK="$BRO/tools/chat_focus_rish.py"
if [[ -f "$PY_HOOK" ]]; then
  if python3 "$PY_HOOK" "$MODE" >>"$LOG" 2>&1; then
    log "CHAT_FOCUS_OK rish hook mode=$MODE"
    echo "CHAT_FOCUS_OK"
    exit 0
  fi
  log "WARN rish hook failed, continuing"
fi

# --- 3) brocc clip-test often opens chat for CLIP_V2 ---
export BRO
if command -v brocc >/dev/null 2>&1; then
  CT="$(brocc clip-test 2>&1)" || true
  echo "$CT" >>"$LOG"
  if echo "$CT" | grep -qE 'PASS CLIP_V2|clip .* PASS'; then
    log "CHAT_FOCUS_OK clip-test"
    echo "CHAT_FOCUS_OK"
    exit 0
  fi
fi

# --- 4) Optional Shizuku / uiautomator dump verify (composer visible) ---
DUMP="$BRO/ui/last_focus_dump.xml"
mkdir -p "$BRO/ui"
if command -v sh >/dev/null 2>&1 && command -v uiautomator >/dev/null 2>&1; then
  uiautomator dump "$DUMP" 2>/dev/null || true
  if [[ -f "$DUMP" ]] && grep -qiE 'EditText|composer|message|Ask' "$DUMP" 2>/dev/null; then
    log "CHAT_FOCUS_OK uiautomator composer hint"
    echo "CHAT_FOCUS_OK"
    exit 0
  fi
fi

log "CHAT_FOCUS_FAIL (no verify)"
echo "CHAT_FOCUS_FAIL" >&2
exit 1
