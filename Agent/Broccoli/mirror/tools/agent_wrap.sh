#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
MODE="${1:-grok}"
shift || true
LOG="$HOME/broccoli/reports/agent_wrap.log"
mkdir -p "$(dirname "$LOG")"
log() { echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

bash "$HOME/aim_rish_ensure.sh" 2>/dev/null || true

case "$MODE" in
  termux|paste-termux)
    # Paste clipboard into THIS Termux session (you: copy code block first)
    CLIP="$(termux-clipboard-get 2>/dev/null || true)"
    if [ -z "$CLIP" ]; then
      log "termux: clipboard empty"
      exit 1
    fi
    printf '%s\n' "$CLIP"
    log "termux: pasted clipboard to stdout (${#CLIP} chars) — pipe or eval as needed"
    ;;
  grok|ask)
    PROMPT="${*:-}"
    if [ -z "$PROMPT" ] && [ ! -t 0 ]; then PROMPT="$(cat)"; fi
    if [ -z "$PROMPT" ]; then
      PROMPT="$(termux-clipboard-get 2>/dev/null || true)"
    fi
    if [ -z "$PROMPT" ]; then
      log "grok: no prompt"
      exit 2
    fi
    log "grok: compose+send len=${#PROMPT}"
    "$HOME/brocc" launch-grok 2>/dev/null || true
    sleep 3
    OUT="$(python3 "$HOME/broccoli/lib/grok_send_tap.py" "$PROMPT" 2>&1)" || RC=$?
    RC="${RC:-0}"
    log "grok_send_tap: $OUT rc=$RC"
    if [ "$RC" != "0" ]; then
      log "fallback brocc grok-send"
      "$HOME/brocc" grok-send "$PROMPT" 2>&1 | tee -a "$LOG" || true
    fi
    sleep 2
    "$HOME/brocc" grok-ask "$PROMPT" 2>&1 | tail -20 | tee -a "$LOG"
    ;;
  gemini|spec)
    PROMPT_FILE="${1:-$HOME/broccoli/spec/PULL_SPEC_PROMPT.txt}"
    test -f "$PROMPT_FILE" || { log "missing $PROMPT_FILE"; exit 3; }
    termux-clipboard-set < "$PROMPT_FILE"
    am start -a android.intent.action.VIEW -d "https://gemini.google.com/app"  2>/dev/null \
      || am start -n com.google.android.apps.bard/.shellapp.ShellActivity 2>/dev/null || true
    sleep 4
    python3 "$HOME/broccoli/lib/grok_send_tap.py" "$(cat "$PROMPT_FILE")" 2>/dev/null || true
    bash "$HOME/aim_ask_once.sh" 180 "$(cat "$PROMPT_FILE")" 2>&1 | tee -a "$LOG" | tail -25
    ;;
  run|code)
    # Copy script to clipboard on PC, then: agent_wrap.sh run | bash
    CLIP="$(termux-clipboard-get 2>/dev/null || true)"
    echo "$CLIP" > "$HOME/broccoli/sandbox/run_clip.sh"
    chmod +x "$HOME/broccoli/sandbox/run_clip.sh"
    log "run: executing sandbox/run_clip.sh"
    bash "$HOME/broccoli/sandbox/run_clip.sh" 2>&1 | tee -a "$LOG"
    ;;
  *)
    echo "usage: agent_wrap.sh grok|PROMPT | gemini | termux | run"
    exit 2
    ;;
esac
