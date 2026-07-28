#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

H = Path.home()

def run(cmd, t=60):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    except subprocess.TimeoutExpired:
        class R:
            returncode = 124
            stdout = "TIMEOUT %ss" % t
            stderr = ""
        return R()

def cycle():
    if os.environ.get("BROCC_AGENT_SKIP_SMOKE") != "1":
        r = run(
            "export BROCCOLI_SMOKE_FORCE=1; python3 ~/broccoli_bootstrap.py grok-smoke 2>&1 | tail -5",
            int(os.environ.get("BROCC_AGENT_SMOKE_TIMEOUT", "45")),
        )
        print("smoke", r.returncode, (r.stdout or "")[:300])
    else:
        print("SMOKE_SKIP")
    r = run("python3 ~/broccoli_clipboard.py test 2>&1 | tail -3", 30)
    print("clip", r.returncode, (r.stdout or "")[:200])
    if (H / "broccoli_rish_pull.py").is_file():
        r = run("python3 ~/broccoli_rish_pull.py 2>&1 | tail -3", 120)
        print("pull", r.returncode, (r.stdout or "")[:200])
    return 0

def health_full():
    return cycle()

def repair():
    if (H / "broccoli_storage_sync.py").is_file():
        run("python3 ~/broccoli_storage_sync.py sync 80", 180)
    return 0

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cycle"
    fn = {"cycle": cycle, "health-full": health_full, "repair": repair}.get(cmd, cycle)
    sys.exit(fn() or 0)
