#!/usr/bin/env python3
import os, re, subprocess, sys, time
ROOT = os.environ.get("BROCC_ROOT", os.path.expanduser("~/broccoli"))
DUMP = "/sdcard/broccoli_window_dump.xml"

def snap():
    try:
        subprocess.run(["bash", os.path.join(ROOT, "ui_snapshot.sh")],
                         cwd=ROOT, timeout=22, capture_output=True)
    except subprocess.TimeoutExpired:
        print("[poll] snap_timeout stale_ok", flush=True)

def btn():
    try:
        x = open(DUMP, encoding="utf-8", errors="ignore").read().lower()
    except Exception:
        return "unknown"
    if "stop" in x: return "stop"
    if "listen" in x: return "listen"
    if "send" in x: return "send"
    return "unknown"

def until(target, timeout, iv=0.4, need=2):
    t0, streak = time.time(), 0
    while time.time() - t0 < timeout:
        snap()
        s = btn()
        print("[poll]", s, flush=True)
        streak = streak + 1 if s == target else 0
        if streak >= need:
            return True
        time.sleep(iv)
    return False

if __name__ == "__main__":
    until("stop", 45) or print("[poll] WARN no_stop", flush=True)
    until("listen", 120) or print("[poll] WARN no_listen", flush=True)
    print("[poll] done", flush=True)
    sys.exit(0)
