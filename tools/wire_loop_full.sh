#!/data/data/com.termux/files/usr/bin/bash
# Grok <-> Termux: send queue head, dump, extract code, run newest block — no manual ~ $ paste.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
export BROCC_NO_CHROME=1
LOG="$HOME/broccoli/reports/wire_loop.log"
POLL=2
MAX_WAIT=14
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

dump(){ bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null; }
launch(){ bash "$HOME/broccoli/lib/launch_grok_native.sh"; sleep 1; }

grok_fg(){
  grep -q 'package="ai.x.grok"' "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null
}

send_msg(){
  MSG="$1"
  termux-clipboard-set <<< "$MSG"
  bash "$HOME/broccoli/tools/codevel_wire_fast.sh" out "$MSG" 2>&1 | tee -a "$LOG" | tail -8
}

read_in(){
  bash "$HOME/broccoli/tools/codevel_wire_fast.sh" in 2>&1 | tee -a "$LOG" | tail -12
}

extract_and_run(){
  python3 "$HOME/broccoli/tools/extract_grok_code.py" 2>&1 | tee -a "$LOG"
  NEWEST="$(ls -t "$HOME/broccoli/sandbox/from_grok"/block_*.sh 2>/dev/null | head -1)"
  if [ -n "$NEWEST" ] && [ -s "$NEWEST" ]; then
    log "RUN $NEWEST"
    bash "$NEWEST" 2>&1 | tee -a "$LOG" | tail -25
    return 0
  fi
  log "no code block in dump yet"
  return 1
}

one_round(){
  LINE="$(grep -v '^#' "$HOME/broccoli/queue/pending.txt" 2>/dev/null | head -1)"
  case "$LINE" in ASK|*) PROMPT="${LINE#ASK|}" ;; *) PROMPT="${LINE:-Continue broccoli co-dev: UI dump only; fix rish dump path; no Chrome}" ;; esac
  launch
  dump
  if ! grok_fg; then
    bash "$HOME/broccoli/tools/toast_user.sh" "Foreground Grok (ai.x.grok) for wire" 2>/dev/null || true
    return 2
  fi
  BEFORE="$(python3 "$HOME/broccoli/tools/ui_dump_chat.py" last 2>/dev/null || true)"
  send_msg "$PROMPT"
  t=0
  while [ "$t" -lt "$MAX_WAIT" ]; do
    sleep "$POLL"
    dump
    AFTER="$(python3 "$HOME/broccoli/tools/ui_dump_chat.py" last 2>/dev/null || true)"
    if [ -n "$AFTER" ] && [ "$AFTER" != "$BEFORE" ] && [ "${#AFTER}" -gt 3 ]; then
      log "reply_seen"
      break
    fi
    t=$((t+POLL))
  done
  read_in
  extract_and_run || true
  echo "ROUND_OK"
}

case "${1:-once}" in
  once) one_round ;;
  loop)
    log "LOOP start"
    while true; do one_round 2>/dev/null || sleep 5; sleep 6; done
    ;;
  show)
    bash "$HOME/broccoli/tools/show_queue.sh"
    cat "$HOME/broccoli/TASK_LIST.md" 2>/dev/null
    ;;
  *)
    echo "usage: wire_loop_full.sh once|loop|show"
    exit 2
    ;;
esac
