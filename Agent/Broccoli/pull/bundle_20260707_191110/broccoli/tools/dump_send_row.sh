#!/data/data/com.termux/files/usr/bin/bash
bash "$HOME/broccoli/lib/ui_dump_rish.sh" >/dev/null 2>&1 || exit 1
python3 <<'PY'
import re, json
from pathlib import Path
x = Path.home().joinpath("broccoli/ui/last_ui.xml").read_text(errors="replace")
cy=cx2=0
m=re.search(r'chat_text_input[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',x) or re.search(r'EditText[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',x)
if m: cy=(int(m.group(2))+int(m.group(4)))//2; cx2=int(m.group(3))
VOICE=re.compile(r"voice|mic|microphone|speech|record|audio",re.I)
cands=[]
for m in re.finditer(r"<node([^>]+)/?>",x):
 a=m.group(1)
 if 'clickable="true"' not in a: continue
 rid=re.search(r'resource-id="([^"]*)"',a); rid=rid.group(1) if rid else ""
 b=re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',a)
 if not b: continue
 x1,y1,x2,y2=map(int,b.groups()); my=(y1+y2)//2
 if cy and abs(my-cy)>200: continue
 blob=(rid+a).lower()
 if VOICE.search(blob): continue
 cands.append({"rid":rid,"cx":(x1+x2)//2,"cy":my,"x1":x1,"send":"send" in blob or "submit" in blob})
if not cands: raise SystemExit(2)
pick=max(cands,key=lambda c:(c["send"],c["x1"]))
Path.home().joinpath("broccoli/meta/send_pick.txt").write_text(f"{pick['cx']} {pick['cy']} {pick['rid']}\n")
print("PICK",pick["rid"],pick["cx"],pick["cy"])
PY
