#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
python3 <<'PY'
import json, time
from pathlib import Path
B = Path.home() / "broccoli"
dump = B / "reports/ui_dump.xml"
if not dump.is_file():
    raise SystemExit(0)
import subprocess
r = subprocess.run(
    ["python3", str(B / "tools/parse_grok_ui.py"), str(dump)],
    capture_output=True, text=True, timeout=15,
)
if r.returncode != 0:
    raise SystemExit(0)
d = json.loads(r.stdout or "{}")
lines = d.get("visible_text") or []
if not lines:
    raise SystemExit(0)
inbox = B / "inbox/chat_lines.txt"
new = "\n".join(lines[-8:])[-4000:]
prev = inbox.read_text(errors="replace") if inbox.is_file() else ""
if new.strip() and new.strip() != prev.strip():
    inbox.write_text(new)
    (B / "meta/last_inbox_ts").write_text(str(int(time.time())))
PY
