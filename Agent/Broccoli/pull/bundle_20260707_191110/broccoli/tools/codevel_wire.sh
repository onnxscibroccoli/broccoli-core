#!/data/data/com.termux/files/usr/bin/bash
# Co-dev wire: Grok chat <-> Termux via UI dumps only.
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
GROK_PKG=ai.x.grok
LOG="$HOME/broccoli/reports/wire.log"
THREAD="$HOME/broccoli/thread/conversation.md"
DUMP_LOCAL="$HOME/broccoli/ui/last_ui.xml"
WIRE_STATE="$HOME/broccoli/meta/wire_state.json"

log() { echo "$(date -Iseconds) $*" | tee -a "$LOG"; }

rish_dump() {
  bash "$HOME/aim_rish_ensure.sh" 2>/dev/null || true
  printf 'uiautomator dump --compressed /data/local/tmp/broccoli_ui.xml\n' | rish 2>/dev/null || true
  sleep 0.5
  if [ -r /data/local/tmp/broccoli_ui.xml ]; then
    cp -f /data/local/tmp/broccoli_ui.xml "$DUMP_LOCAL"
  else
    printf 'cat /data/local/tmp/broccoli_ui.xml\n' | rish 2>/dev/null > "$DUMP_LOCAL" || true
  fi
  wc -c "$DUMP_LOCAL" 2>/dev/null | awk '{print $1}'
}

launch_grok() { bash "$HOME/broccoli/lib/launch_grok_native.sh"; sleep 1; }
  bash "$HOME/broccoli/lib/launch_grok_native.sh"
  sleep 1
}

god_mode_user_primary() {
  rish_dump >/dev/null
  python3 -c "
import json, subprocess
r = json.loads(subprocess.check_output(['python3','$HOME/broccoli/tools/ui_dump_chat.py','report'], text=True))
import sys
sys.exit(0 if r.get('grok_fg') else 2)
" 2>/dev/null
}

wire_in() {
  log "WIRE-IN dump"
  launch_grok
  nbytes=$(rish_dump || echo 0)
  REPORT=$(python3 "$HOME/broccoli/tools/ui_dump_chat.py" report)
  echo "$REPORT" > "$WIRE_STATE"
  if ! echo "$REPORT" | python3 -c "import sys,json; r=json.load(sys.stdin); sys.exit(0 if r.get('grok_fg') else 1)"; then
    bash "$HOME/broccoli/tools/toast_user.sh" "Open Grok (ai.x.grok) — co-dev needs chat foreground"
    log "WIRE-IN skip: user primary (Grok not in dump). Retry when Grok foreground."
    echo "GODMODE: user has phone — Grok not foreground. Open Grok or run: wire-out MSG"
    return 2
  fi
  {
    echo ""
    echo "## wire-in $(date -Iseconds) bytes=$nbytes"
    python3 "$HOME/broccoli/tools/ui_dump_chat.py" lines
  } >> "$THREAD"
  echo "----- GROK CHAT (from UI dump) -----"
  python3 "$HOME/broccoli/tools/ui_dump_chat.py" lines | tail -20
  echo "----- last -----"
  python3 "$HOME/broccoli/tools/ui_dump_chat.py" last
  echo "----- dump ok: composer=$(echo "$REPORT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('has_composer'))") send=$(echo "$REPORT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('has_send'))") -----"
  log "WIRE-IN done"
}

wire_out() {
  MSG="${1:-}"
  if [ -z "$MSG" ] && [ ! -t 0 ]; then MSG="$(cat)"; fi
  if [ -z "$MSG" ]; then MSG="$(termux-clipboard-get 2>/dev/null || true)"; fi
  if [ -z "$MSG" ]; then
    echo "usage: codevel_wire.sh out 'your prompt'" >&2
    exit 2
  fi
  log "WIRE-OUT len=${#MSG}"
  launch_grok
  rish_dump >/dev/null
  REPORT=$(python3 "$HOME/broccoli/tools/ui_dump_chat.py" report)
  HAS_C=$(echo "$REPORT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('has_composer'))")
  HAS_S=$(echo "$REPORT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('has_send'))")
  if [ "$HAS_C" != "True" ]; then
    bash "$HOME/broccoli/tools/toast_user.sh" "Grok: tap Ask tab — no composer in UI dump"
    log "WIRE-OUT adapt: no composer in dump — tap Ask tab area"
    python3 <<'PY'
import json, subprocess, re
from pathlib import Path
xml = Path.home().joinpath("broccoli/ui/last_ui.xml").read_text(errors="replace")
for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    if re.search(r'^Ask$', m.group(1), re.I):
        x,y=(int(m.group(2))+int(m.group(4)))//2,(int(m.group(3))+int(m.group(5)))//2
        subprocess.run(["bash","-c",f'printf "input tap {x} {y}\\n" | rish'], check=False)
        print("tapped Ask", x, y)
        break
PY
    sleep 2
    rish_dump >/dev/null
  fi
  termux-clipboard-set <<< "$MSG"
  GROK_PKG=ai.x.grok python3 "$HOME/broccoli/lib/grok_send_tap.py" "$MSG" 2>&1 | tee -a "$LOG" || {
    log "WIRE-OUT adapt: grok_send_tap failed — rish paste+enter"
    printf 'input keyevent 279\ninput keyevent 66\n' | rish 2>/dev/null || true
  }
  sleep 8
  rish_dump >/dev/null
  echo "----- after send (dump) -----"
  python3 "$HOME/broccoli/tools/ui_dump_chat.py" lines | tail -15
  LAST=$(python3 "$HOME/broccoli/tools/ui_dump_chat.py" last)
  echo "LAST=$LAST"
  {
    echo ""
    echo "## wire-out $(date -Iseconds)"
    echo "USER: $MSG"
    echo "GROK_LAST: $LAST"
  } >> "$THREAD"
  log "WIRE-OUT done last=${#LAST}"
}

wire_task() {
  LINE="${1:-}"
  if [ -z "$LINE" ] && [ -f "$HOME/broccoli/queue/pending.txt" ]; then
    LINE=$(grep -v '^#' "$HOME/broccoli/queue/pending.txt" | head -1)
  fi
  case "$LINE" in
    ASK|*) wire_out "${LINE#ASK|}" ;;
    *) wire_out "$LINE" ;;
  esac
  wire_in || true
}

wire_loop() {
  log "WIRE-LOOP start (god-mode aware)"
  while true; do
    if god_mode_user_primary; then
      wire_in && wire_task 2>/dev/null || true
    else
      log "WIRE-LOOP idle: user primary"
    fi
    sleep 30
  done
}

CMD="${1:-in}"
shift || true
case "$CMD" in
  in|wire-in)     wire_in ;;
  out|wire-out)   wire_out "$*" ;;
  task)           wire_task "$*" ;;
  dump)           launch_grok; rish_dump; python3 "$HOME/broccoli/tools/ui_dump_chat.py" report ;;
  loop)           wire_loop ;;
  open|codevel)   launch_grok; bash "$HOME/broccoli/tools/dismiss_tos_grok.sh" 2>/dev/null || true; wire_in ;;
  *)
    echo "usage: codevel_wire.sh in|out MSG|task|dump|loop|open"
    exit 2
    ;;
esac
