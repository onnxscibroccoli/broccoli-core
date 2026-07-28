#!/data/data/com.termux/files/usr/bin/bash
B="$HOME/broccoli"
python3 <<'PY'
import json, subprocess, time
from pathlib import Path
B = Path.home() / "broccoli"
dump = B / "reports/ui_dump.xml"
parse = {}
if dump.is_file():
    r = subprocess.run(["python3", str(B / "tools/parse_grok_ui.py"), str(dump)], capture_output=True, text=True, timeout=20)
    if r.returncode == 0:
        parse = json.loads(r.stdout or "{}")
def pg(p):
    try:
        return subprocess.run(["pgrep", "-af", p], capture_output=True, text=True, timeout=2).stdout.strip().splitlines()[:2]
    except Exception:
        return []
df = subprocess.run("df -k $HOME | awk 'NR==2{print int($4/1024)}'", shell=True, capture_output=True, text=True)
h = {
    "ts": time.time(),
    "avail_mb": df.stdout.strip(),
    "collab": pg("collab_rish_loop"),
    "daemon": pg("broccoli-daemon"),
    "dump_ok": parse.get("ok"),
    "dump_bytes": parse.get("bytes"),
    "composer": bool(parse.get("composer")),
    "task_queued": (B / "queue/agent_task.txt").is_file() and (B / "queue/agent_task.txt").stat().st_size > 0,
}
(B / "meta/agent_health.json").write_text(json.dumps(h, indent=2))
print(json.dumps(h))
PY
