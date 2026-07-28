#!/usr/bin/env python3
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path.home() / "broccoli/lib"))
from display_lane import load_policy, enable_user_primary, enable_automation_secondary, may_run_foreground_ui, user_is_idle
cmd = (sys.argv[1] if len(sys.argv)>1 else "status").lower()
if cmd in ("on","user-primary"): print(json.dumps(enable_user_primary()))
elif cmd in ("off","secondary"): print(json.dumps(enable_automation_secondary()))
elif cmd == "may-run": print("yes" if may_run_foreground_ui() else "no")
elif cmd == "status":
    p = load_policy()
    print(json.dumps({**p, "user_idle": user_is_idle(), "may_run_ui": may_run_foreground_ui()}, indent=2))
else: print("usage: on|off|status|may-run"); sys.exit(1)
