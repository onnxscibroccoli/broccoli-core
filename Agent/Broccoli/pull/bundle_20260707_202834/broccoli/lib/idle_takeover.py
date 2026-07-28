#!/usr/bin/env python3
import json, subprocess, sys, time
from pathlib import Path

ROOT = Path.home() / "broccoli"
POLICY = ROOT / "meta" / "idle_policy.json"
sys.path.insert(0, str(ROOT / "lib"))

def toast(msg):
    subprocess.run(["termux-toast", "-g", "center", msg[:120]], timeout=8, capture_output=True)
    print("TOAST", msg, flush=True)

def wait_idle_then_grok_takeover():
    from idle_detect import user_touched_recently
    p = json.loads(POLICY.read_text()) if POLICY.exists() else {}
    need = int(p.get("idle_seconds_before_takeover", 10))
    countdown = p.get("countdown_seconds", [3, 2, 1])
    thresh = float(p.get("input_active_threshold_sec", 2.0))

    toast(f"{need}s → Grok CHAT")
    t0 = time.time()
    while time.time() - t0 < need:
        if user_touched_recently(thresh):
            t0 = time.time()
        time.sleep(1)
    if user_touched_recently(thresh):
        toast("Touch abort")
        return False
    for n in countdown:
        toast(f"Chat in {n}")
        time.sleep(1)
    toast("Open chat now")
    r = subprocess.run([sys.executable, str(ROOT / "lib" / "grok_chat_foreground.py")], timeout=320)
    return r.returncode == 0

if __name__ == "__main__":
    sys.exit(0 if wait_idle_then_grok_takeover() else 2)
