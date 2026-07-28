#!/usr/bin/env python3
import subprocess, sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path.home() / "broccoli/lib"))
from display_lane import enable_automation_secondary, enable_user_primary, load_policy
from brocc_toast import toast
def main():
    toast("Broki: Google AI Mode test (secondary lane)")
    enable_automation_secondary()
    rec = {"ts": time.time(), "test": "google_ai_secondary", "policy": load_policy()}
    (Path.home() / "broccoli/meta/google_secondary_test.json").write_text(json.dumps(rec, indent=2))
    q = "Android UI automation Shizuku Termux accessibility patterns"
    for cmd in (
        ["brocc", "research", "round"],
        ["python3", str(Path.home() / "broccoli_research.py"), "round"],
        ["python3", str(Path.home() / "google_ai_bootstrap.py"), "research", q],
    ):
        try:
            r = subprocess.run(cmd, timeout=180, capture_output=True, text=True)
            if r.returncode == 0:
                print("OK", cmd); break
        except Exception as e:
            print("skip", e)
    enable_user_primary(8)
    toast("Broki: Google test done — phone back")
    print('{"done": true}')
if __name__ == "__main__": main()
