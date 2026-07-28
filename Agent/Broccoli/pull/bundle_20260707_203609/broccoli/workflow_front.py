#!/usr/bin/env python3
import json, subprocess, sys, time
from pathlib import Path
HOME, ROOT = Path.home(), Path.home() / "broccoli"
META, REP, RES = ROOT / "meta", ROOT / "reports", ROOT / "research"
BOOT = HOME / "broccoli_bootstrap.py"
sys.path.insert(0, str(ROOT / "lib"))
try:
    from toast import step, toast
except Exception:
    def step(m): print(m, flush=True)
    def toast(m): print(m, flush=True)

def run(cmd, t=90):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    except Exception as e:
        return type("R", (), {"stdout": "", "stderr": str(e), "returncode": -1})()

def grok_focused():
    r = run("dumpsys window 2>/dev/null | grep -iE 'mCurrentFocus|mFocusedApp' | grep -i grok | head -1", 12)
    return "grok" in (r.stdout or "").lower()

def main():
    step("Front gate")
    try:
        sys.path.insert(0, str(ROOT / "lib"))
        from task_queue import started, done, failed, note, rebuild_context
        started("workflow_front", detail="launch+smoke heal")
    except Exception:
        pass

    if BOOT.exists() and not grok_focused():
        step("Launch Grok")
        run(f'python3 "{BOOT}" launch_grok', 45)
        time.sleep(2)
    subprocess.run([sys.executable, str(ROOT / "smoke_fast.py")], timeout=90)
    subprocess.run([sys.executable, str(ROOT / "broccoli_meta_heal.py")], timeout=90)
    cache = {}
    cf = META / "smoke_cache.json"
    if cf.exists():
        try: cache = json.loads(cf.read_text())
        except Exception: pass
    smoke_pass = cache.get("status") == "PASS"
    notes = (RES / "notes.md").read_text(errors="replace").splitlines() if (RES / "notes.md").exists() else []
    ready = smoke_pass and len(notes) >= 5
    REP.mkdir(parents=True, exist_ok=True)
    (REP / "workflow_front.txt").write_text(f"TASK_READY={ready}\nSMOKE={cache.get('status')}\nGROK_FOCUS={grok_focused()}\n")
    toast("TASK_READY" if ready else ("Smoke OK" if smoke_pass else "Front done"))
    print("TASK_READY" if ready else "FRONT_DONE")
    return 0

if __name__ == "__main__":
    sys.exit(main())
