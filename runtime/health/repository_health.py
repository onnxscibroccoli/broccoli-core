#!/usr/bin/env python3

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def run(cmd):
    p = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        capture_output=True
    )
    return p.stdout.strip()

status = run(["git", "status", "--porcelain"])
branch = run(["git", "branch", "--show-current"])
head = run(["git", "rev-parse", "--short", "HEAD"])
upstream = run(["git", "rev-parse", "--abbrev-ref", "@{u}"])

try:
    ahead_behind = run(["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"])
except Exception:
    ahead_behind = "0\t0"

untracked = [
    x[3:]
    for x in status.splitlines()
    if x.startswith("?? ")
]

modified = [
    x
    for x in status.splitlines()
    if not x.startswith("??")
]

report = {
    "timestamp": int(time.time()),
    "branch": branch,
    "commit": head,
    "upstream": upstream,
    "ahead_behind": ahead_behind,
    "clean": len(status) == 0,
    "modified": modified,
    "untracked": untracked,
}

outdir = ROOT / "runtime" / "event_bus" / "processed"
outdir.mkdir(parents=True, exist_ok=True)

outfile = outdir / f"repo_{int(time.time())}.json"

outfile.write_text(json.dumps(report, indent=2))

print(json.dumps(report, indent=2))
print(f"\nRepository health written to {outfile}")
