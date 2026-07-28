#!/usr/bin/env python3
"""After idle: launch Grok, focus, run front gate + smoke B+C."""
import subprocess, sys, time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "broccoli"
BOOT = HOME / "broccoli_bootstrap.py"
PKG = "ai.x.grok"

def run(cmd, t=90):
    print("GROK_TAKEOVER", cmd[:140], flush=True)
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    except Exception as e:
        return type("R", (), {"stdout": "", "stderr": str(e), "returncode": -1})()

def toast(msg):
    subprocess.run(["termux-toast", "-g", "center", msg[:120]], timeout=8, capture_output=True)
    print("TOAST", msg, flush=True)

def grok_focused():
    r = run("dumpsys window windows 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | head -2", 12)
    return PKG in (r.stdout or "").lower()

def takeover():
    toast("Grok takeover")
    if BOOT.exists():
        run(f'python3 "{BOOT}" launch_grok', 45)
        time.sleep(1.5)
    if not grok_focused():
        run(f'monkey -p {PKG} -c android.intent.category.LAUNCHER 1 2>/dev/null', 20)
        time.sleep(2)
    run(f'python3 "{ROOT}/workflow_front.py" 2>/dev/null || true', 150)
    run(f'python3 "{ROOT}/broccoli_meta_heal.py" 2>/dev/null || true', 90)
    try:
        sys.path.insert(0, str(ROOT / "lib"))
        from task_queue import note, rebuild_context
        note("grok_takeover completed")
        rebuild_context()
    except Exception:
        pass
    toast("Grok cycle done")
    return grok_focused()

if __name__ == "__main__":
    ok = takeover()
    sys.exit(0 if ok else 1)
