#!/usr/bin/env python3
import json, os, subprocess, sys, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "lib"))
from rish_cmd import tap, keyevent

SX = int(os.environ.get("BROCC_SEND_X", "987"))
SY = int(os.environ.get("BROCC_SEND_Y", "1343"))

def st():
    r = subprocess.run(["python3", os.path.join(ROOT, "screen_state.py")],
                       capture_output=True, text=True, timeout=15, cwd=ROOT)
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}

s = st()
if not (s.get("on_grok") or s.get("fg_package") == "ai.x.grok"):
    print("SEND_ABORT", s.get("fg_package"), flush=True)
    sys.exit(2)

for _ in range(2):
    keyevent(4)
    time.sleep(0.3)

print("[tap_send] dismiss_kb one_tap", SX, SY, flush=True)
tap(SX, SY, jitter=4)
time.sleep(0.45)
print("SEND_OK", flush=True)
sys.exit(0)
