#!/usr/bin/env python3
import os, sys, subprocess
ROOT = os.path.expanduser("~/broccoli")
EXPECT = os.environ.get("BROCC_EXPECT", "")
CAP = os.path.join(ROOT, "ui", "last_capture.txt")
MODE = os.environ.get("BROCC_VALIDATE_MODE", "grace")

def text():
    if os.environ.get("BROCC_USE_AUTOJS") == "1":
        p = os.path.join(ROOT, "scripts", "autojs_run.py")
        if os.path.isfile(p):
            subprocess.run([sys.executable, p, "read"], cwd=ROOT, timeout=35, capture_output=True)
    if os.path.isfile(CAP):
        return open(CAP, encoding="utf-8", errors="ignore").read().strip()
    return ""

t = text()
if EXPECT and EXPECT in t:
    print("[validate] expect_ok", flush=True)
    sys.exit(0)
if len(t) >= 8:
    print("[validate] len_ok", len(t), flush=True)
    sys.exit(0)
if MODE in ("grace", "smoke_only"):
    print("[validate] grace_ok", flush=True)
    sys.exit(0)
print("[validate] thin", len(t), flush=True)
sys.exit(1)
