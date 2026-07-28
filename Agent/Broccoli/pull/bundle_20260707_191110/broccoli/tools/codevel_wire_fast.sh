#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
GROK_PKG=ai.x.grok
LOG="$HOME/broccoli/reports/wire.log"
POLL=2
WAIT_REPLY=12
STEP=0.4
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }
toast(){ bash "$HOME/broccoli/tools/toast_user.sh" "$1" 2>/dev/null || true; }

dump(){ bash "$HOME/broccoli/lib/ui_dump_rish.sh"; }

ensure_grok(){
  if bash "$HOME/broccoli/lib/grok_foreground.sh" 2>/dev/null; then
    return 0
  fi
  bash "$HOME/broccoli/lib/launch_grok_native.sh"
  sleep 1
  dump >/dev/null
  bash "$HOME/broccoli/lib/grok_foreground.sh" 2>/dev/null
}

bounds_tap(){
  python3 - "$1" <<'PY'
import re, subprocess, sys
pat = sys.argv[1]
from pathlib import Path
xml = Path.home().joinpath("broccoli/ui/last_ui.xml").read_text(errors="replace")
for m in re.finditer(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*(?:text|content-desc)="([^"]*)"', xml):
    pass
for m in re.finditer(r'(?:text|content-desc)="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    if re.search(pat, m.group(1), re.I):
        x,y=(int(m.group(2))+int(m.group(4)))//2,(int(m.group(3))+int(m.group(5)))//2
        subprocess.run(["bash","-c", f'printf "input tap {x} {y}\\n" | rish'], check=False)
        print(x,y); break
PY
}

composer_send(){
  python3 <<'PY'
import re, subprocess
from pathlib import Path
xml = Path.home().joinpath("broccoli/ui/last_ui.xml").read_text(errors="replace")
comp=None
for m in re.finditer(r'resource-id="([^"]*chat_text_input[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    comp=tuple(map(int,m.groups()[1:5])); break
if not comp:
    for m in re.finditer(r'class="[^"]*EditText"[^>]*package="ai\.x\.grok"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        comp=tuple(map(int,m.groups())); break
if not comp:
    for m in re.finditer(r'class="[^"]*EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*package="ai\.x\.grok"', xml):
        comp=tuple(map(int,m.groups())); break
if comp:
    x,y=(comp[0]+comp[2])//2,(comp[1]+comp[3])//2
    subprocess.run(["bash","-c", f'printf "input tap {x} {y}\\n" | rish'], check=False)
cy=y
send=None
for m in re.finditer(r'clickable="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    x1,y1,x2,y2=map(int,m.groups())
    cy2=(y1+y2)//2
    chunk=xml[m.start():m.start()+400]
    if cy2 < cy-50: continue
    if re.search(r'send|submit|ImageButton', chunk, re.I):
        send=(x1+x2)//2,cy2; break
if send:
    subprocess.run(["bash","-c", f'printf "input tap {send[0]} {send[1]}\\n" | rish'], check=False)
    print("send_tap", send)
else:
    subprocess.run(["bash","-c", 'printf "input keyevent 66\\n" | rish'], check=False)
    print("send_enter")
PY
}

wire_in(){
  log "IN"
  dump >/dev/null || true
  if ! ensure_grok; then
    toast "Open Grok app — wire needs ai.x.grok in UI dump"
    return 2
  fi
  python3 "$HOME/broccoli/tools/ui_dump_chat.py" lines 2>/dev/null | tail -18
  python3 "$HOME/broccoli/tools/ui_dump_chat.py" last 2>/dev/null
}

wire_out(){
  MSG="${1:-}"
  [ -z "$MSG" ] && MSG="$(termux-clipboard-get 2>/dev/null || true)"
  [ -z "$MSG" ] && { echo "need message"; exit 2; }
  log "OUT len=${#MSG}"
  ensure_grok || { toast "Foreground Grok first"; return 2; }
  dump >/dev/null
  if ! grep -q chat_text_input "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null && ! grep -q 'EditText' "$HOME/broccoli/ui/last_ui.xml" | grep -q grok; then
    bounds_tap '^Ask$' 2>/dev/null || true
    sleep "$STEP"
    dump >/dev/null
  fi
  termux-clipboard-set <<< "$MSG"
  printf 'input tap 0 0\n' | rish >/dev/null 2>&1 || true
  composer_send
  sleep "$STEP"
  printf 'input keyevent 279\n' | rish
  sleep "$STEP"
  composer_send
  # poll reply — fast loop, no 8s block
  t=0
  before="$(python3 "$HOME/broccoli/tools/ui_dump_chat.py" last 2>/dev/null || true)"
  while [ "$t" -lt "$WAIT_REPLY" ]; do
    sleep "$POLL"
    dump >/dev/null
    after="$(python3 "$HOME/broccoli/tools/ui_dump_chat.py" last 2>/dev/null || true)"
    if [ -n "$after" ] && [ "$after" != "$before" ] && [ "$after" != "$MSG" ]; then
      echo "REPLY=$after"
      log "OUT reply ok"
      return 0
    fi
    t=$((t+POLL))
  done
  toast "No new line in dump yet — run: wire in"
  python3 "$HOME/broccoli/tools/ui_dump_chat.py" lines 2>/dev/null | tail -10
}

wire_loop(){
  log "LOOP fast"
  while true; do
    if ensure_grok 2>/dev/null; then
      head -1 "$HOME/broccoli/queue/pending.txt" 2>/dev/null | grep -v '^#' | while read -r line; do
        case "$line" in ASK|*) wire_out "${line#ASK|}" ;; esac
        wire_in || true
      done
    fi
    sleep 8
  done
}

CMD="${1:-in}"
shift || true
case "$CMD" in
  in) wire_in ;;
  out) wire_out "$*" ;;
  dump) dump; python3 "$HOME/broccoli/tools/ui_dump_chat.py" report ;;
  loop) wire_loop ;;
  launch) bash "$HOME/broccoli/lib/launch_grok_native.sh"; sleep 1; dump; wire_in ;;
  *)
    echo "usage: codevel_wire_fast.sh in|out|dump|loop|launch"
    exit 2 ;;
esac
