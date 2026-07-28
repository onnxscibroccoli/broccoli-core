#!/data/data/com.termux/files/usr/bin/bash
set -eu
export PATH="$HOME/bin:$PATH:/data/data/com.termux/files/usr/bin"
GROK_PKG=ai.x.grok
bash "$HOME/aim_rish_ensure.sh" 2>/dev/null || true
am force-stop com.android.chrome 2>/dev/null || true
monkey -p "$GROK_PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
sleep 4
for round in 1 2 3; do
  printf 'uiautomator dump --compressed /data/local/tmp/broccoli_ui.xml\n' | rish 2>/dev/null || true
  python3 <<'PY'
import re, subprocess, sys
from pathlib import Path
xml = ""
for p in [Path("/data/local/tmp/broccoli_ui.xml"), Path.home()/"broccoli/ui/last_ui.xml"]:
    if p.is_file() and p.stat().st_size > 500:
        xml = p.read_text(encoding="utf-8", errors="replace")
        break
if not xml:
    sys.exit(0)
patterns = [
    r'text="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
    r'content-desc="([^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
]
tos = re.compile(r'accept|agree|continue|got it|i agree|ok|next|start|allow', re.I)
skip = re.compile(r'decline|cancel|disagree|not now', re.I)
tapped = False
for pat in patterns:
    for m in re.finditer(pat, xml):
        label = m.group(1)
        if skip.search(label):
            continue
        if tos.search(label) or re.search(r'terms|privacy|tos', label, re.I):
            x1,y1,x2,y2 = map(int, m.groups()[1:5])
            x,y = (x1+x2)//2, (y1+y2)//2
            subprocess.run(["bash","-c", f'printf "input tap {x} {y}\\n" | rish'], check=False, timeout=15)
            print("TOS_TAP", label[:50], x, y)
            tapped = True
            break
    if tapped:
        break
if not tapped:
    for m in re.finditer(r'clickable="true"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"[^>]*text="([^"]*)"', xml):
        if tos.search(m.group(5)):
            x1,y1,x2,y2 = map(int, m.groups()[:4])
            x,y = (x1+x2)//2, (y1+y2)//2
            subprocess.run(["bash","-c", f'printf "input tap {x} {y}\\n" | rish'], check=False)
            print("TOS_TAP2", m.group(5)[:50])
            break
PY
  sleep 2
done
date -Iseconds > "$HOME/broccoli/meta/tos_dismissed.flag"
