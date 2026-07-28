#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
MSG="$1"
LOG="$HOME/broccoli/reports/wire_send.log"
[ -n "$MSG" ] || exit 2
log(){ echo "$(date -Iseconds) $*" | tee -a "$LOG"; }
log "SEND start len=${#MSG}"
date +%s > "$HOME/broccoli/meta/automation_lock.ts"

launch(){ timeout 8 bash "$HOME/broccoli/lib/launch_grok_native.sh" >/dev/null 2>&1 || true; sleep 1.2; }

tap_ask(){
  python3 <<'PY'
import re, subprocess
from pathlib import Path
p = Path.home() / "broccoli/ui/last_ui.xml"
if not p.is_file(): raise SystemExit(0)
xml = p.read_text(errors="replace")
for m in re.finditer(r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    if m.group(1).strip().lower() == "ask":
        x,y=(int(m.group(2))+int(m.group(4)))//2,(int(m.group(3))+int(m.group(5)))//2
        subprocess.run(["bash","-c",f'printf "input tap {x} {y}\\n" | rish'], check=False, timeout=8)
        print("tap_ask", x, y); break
PY
}

focus_paste_send(){
  python3 <<'PY'
import re, subprocess, os
from pathlib import Path
xml = Path.home().joinpath("broccoli/ui/last_ui.xml").read_text(errors="replace")
comp = None
for m in re.finditer(r'resource-id="([^"]*chat_text_input[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    comp = tuple(map(int, m.groups()[1:5])); break
if not comp:
    for m in re.finditer(r'class="[^"]*EditText"[^>]*package="ai\.x\.grok"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
        comp = tuple(map(int, m.groups())); break
if not comp:
    print("NO_COMPOSER"); raise SystemExit(1)
x,y=(comp[0]+comp[2])//2,(comp[1]+comp[3])//2
subprocess.run(["bash","-c",f'printf "input tap {x} {y}\\n" | rish'], check=False, timeout=8)
cy=(comp[1]+comp[3])//2
send=None
for m in re.finditer(r'clickable="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    y1,y2=int(m.group(2)),int(m.group(4))
    if (y1+y2)//2 < cy-50: continue
    if re.search(r'send|submit|ImageButton', xml[m.start():m.start()+400], re.I):
        send=((int(m.group(1))+int(m.group(3)))//2,(y1+y2)//2); break
print("COMP", x, y, "SEND", send)
PY
  termux-clipboard-set <<< "$MSG"
  timeout 5 bash "$HOME/broccoli/lib/adb_rish.sh" "input keyevent 279" >/dev/null 2>&1 || true
  sleep 0.35
  timeout 5 bash "$HOME/broccoli/lib/adb_rish.sh" "input keyevent 279" >/dev/null 2>&1 || true
  sleep 0.25
  python3 <<'PY2'
import re, subprocess
from pathlib import Path
xml = Path.home().joinpath("broccoli/ui/last_ui.xml").read_text(errors="replace")
cy=0
for m in re.finditer(r'chat_text_input[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    cy=(int(m.group(2))+int(m.group(4)))//2; break
for m in re.finditer(r'clickable="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml):
    if (int(m.group(2))+int(m.group(4)))//2 < cy-50: continue
    if re.search(r'send|submit', xml[m.start():m.start()+350], re.I):
        x,y=(int(m.group(1))+int(m.group(3)))//2,(int(m.group(2))+int(m.group(4)))//2
        subprocess.run(["bash","-c",f'printf "input tap {x} {y}\\n" | rish'], check=False, timeout=8)
        print("send_tap"); raise SystemExit(0)
subprocess.run(["bash","-c",'printf "input keyevent 66\\n" | rish'], check=False, timeout=8)
print("send_enter")
PY2
}

launch
for i in 1 2 3; do
  bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null || true
  grep -q chat_text_input "$HOME/broccoli/ui/last_ui.xml" 2>/dev/null && break
  tap_ask 2>/dev/null || true
  sleep 0.8
done
if ! focus_paste_send 2>>"$LOG"; then
  log "fallback grok_send_tap"
  GROK_PKG=ai.x.grok timeout 25 python3 "$HOME/broccoli/lib/grok_send_tap.py" "$MSG" >>"$LOG" 2>&1 || true
fi
log "SEND done"
date +%s > "$HOME/broccoli/meta/automation_lock.ts"
