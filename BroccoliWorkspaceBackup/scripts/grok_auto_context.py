#!/usr/bin/env python3
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def state():
    r = subprocess.run(["python3", os.path.join(ROOT, "screen_state.py")], capture_output=True, text=True, timeout=12)
    try: return json.loads(r.stdout or "{}")
    except: return {}
st = state()
if not (st.get("on_grok") or st.get("fg_package") == "ai.x.grok"):
    print("CONTEXT_SKIP"); sys.exit(0)
if st.get("can_inject") and st.get("input_xy"):
    print("CONTEXT_OK stay_in_thread"); sys.exit(0)
print("CONTEXT_SKIP"); sys.exit(0)
