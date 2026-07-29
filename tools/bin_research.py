import time
#!/usr/bin/env python3
"""Scan broccoli bin + brocc + loop scripts; write reports/bin_research.json"""
import os, json, time, subprocess, shutil
from pathlib import Path

BRO = Path.home() / "broccoli"
PREFIX = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
OUT = BRO / "reports/bin_research.json"

def sh(cmd, t=25):
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return -1, str(e)

def pgrep(pat):
    rc, out = sh(f"pgrep -af '{pat}' 2>/dev/null || true")
    lines = [ln.strip() for ln in out.splitlines() if ln.strip() and "pgrep" not in ln]
    return lines

LOOPS = [
    ("broccoli_infinite_dev_loop", "infinite_dev"),
    ("broccoli_agentic_loop", "agentic"),
    ("poll_loop", "poll"),
    ("version_walk_heal", "version_walk"),
    ("brocc agent", "brocc_agent"),
    ("agent-loop", "agent_loop_cmd"),
]

bins = []
for d in [BRO / "bin", PREFIX / "bin", Path.home() / "bin"]:
    if d.is_dir():
        for f in sorted(d.iterdir()):
            if f.is_file() and (f.suffix in ("", ".sh", ".py") or "brocc" in f.name.lower() or "broccoli" in f.name.lower()):
                bins.append({"path": str(f), "name": f.name, "size": f.stat().st_size})

tools_loops = []
td = BRO / "tools"
if td.is_dir():
    for pat in ("*loop*", "*agent*", "*poll*", "*wire*", "*start*", "*round*"):
        for f in td.glob(pat):
            if f.is_file():
                tools_loops.append(str(f.relative_to(BRO)))

brocc = shutil.which("brocc") or str(BRO / "bin/brocc")
brocc_help = ""
if Path(brocc).exists() or shutil.which("brocc"):
    _, brocc_help = sh(f"{brocc} --help 2>&1; {brocc} help 2>&1; {brocc} 2>&1", 15)

wire_candidates = []
for name in ("wire", "wire.sh", "broccoli_wire", "brocc-wire", "start_wire"):
    for d in [BRO / "bin", BRO / "tools", PREFIX / "bin"]:
        p = d / name
        if p.is_file():
            wire_candidates.append(str(p))

running = {k: pgrep(p) for p, k in LOOPS}

doc = {
    "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
    "brocc_path": brocc if Path(brocc).exists() else shutil.which("brocc"),
    "wire_candidates": wire_candidates,
    "bins_sample": bins[:40],
    "tools_loops": tools_loops[:50],
    "loops_running": running,
    "brocc_help_head": brocc_help[:2500],
}
OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
print(json.dumps({"ok": True, "report": str(OUT), "running": {k: len(v) for k,v in running.items()}}, indent=2))
