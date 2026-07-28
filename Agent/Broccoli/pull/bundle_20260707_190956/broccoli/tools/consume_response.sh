#!/data/data/com.termux/files/usr/bin/bash
set -eu
B="$HOME/broccoli"
python3 <<'PY'
import json, time, subprocess
from pathlib import Path
B = Path.home() / "broccoli"
dump = B / "reports/ui_dump.xml"
r = subprocess.run(["python3", str(B / "tools/parse_grok_ui.py"), str(dump)], capture_output=True, text=True)
if r.returncode != 0:
    raise SystemExit(0)
d = json.loads(r.stdout or "{}")
lines = d.get("visible_text") or []
if not lines:
    raise SystemExit(0)
last = lines[-1][:2000]
rec = {"ts": time.time(), "role": "assistant", "text": last}
with (B / "thread/conversation.jsonl").open("a") as f:
    f.write(json.dumps(rec) + "\n")
(B / "thread/rolling_summary.txt").write_text(last[:800])
PY
