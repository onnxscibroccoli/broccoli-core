
#!/usr/bin/env python3
"""Agentic Broccoli: health, repair, mac ingest, worker — routine ops without Mac TERMINUX."""
import json, subprocess, sys, time
from pathlib import Path

H, R = Path.home(), Path.home() / "broccoli"
MANUAL = R / "user" / "MANUAL_ONLY"

def run(cmd, t=300):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)

def toast(msg):
    subprocess.run(["termux-toast", "-s", ("Broccoli agent: " + msg)[:100]], timeout=5, check=False)

def health_full():
    issues = []
    if run("shizuku -v", 10).returncode != 0:
        issues.append("shizuku")
    focus = run("shizuku -r sh -c 'dumpsys window | grep mCurrentFocus'", 12).stdout or ""
    if "ai.x.grok" not in focus and "google" not in focus.lower():
        issues.append("focus")
    for f in ("broccoli_bootstrap.py", "broccoli_worker.sh", "broccoli_grok_job.py"):
        if not (H / f).is_file():
            issues.append("missing:" + f)
    return issues

def repair(issues):
    toast("repair " + ",".join(issues[:3]))
    if "shizuku" in issues:
        run("termux-toast -s 'Start Shizuku app manually'", 5)
    if "focus" in issues:
        run("termux-am start -n ai.x.grok/.main.GrokActivity 2>/dev/null", 15)
        time.sleep(2)
    run("python3 ~/broccoli_meta.py heal 2>/dev/null", 60)
    run("python3 ~/broccoli_resilience.py recover 2>/dev/null", 60)
    return health_full()

def cycle():
    if MANUAL.is_file():
        toast("MANUAL_ONLY — no auto cycle")
        return 0
    toast("health")
    issues = health_full()
    if issues:
        issues = repair(issues)
    toast("mac-ingest")
    run("python3 ~/broccoli_mac_ingest.py", 120)
    toast("worker")
    run("python3 ~/broccoli_worker.sh 2>>~/broccoli/daemon.log || bash ~/broccoli_worker.sh", 600)
    toast("smoke check")
    r = run("python3 ~/broccoli_bootstrap.py grok-smoke 2>&1 | tail -3", 120)
    if "PASS" not in (r.stdout or ""):
        toast("smoke FAIL — see log")
    else:
        toast("cycle done OK")
    return 0

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "cycle"
    if cmd == "health-full":
        print(json.dumps(health_full())); sys.exit(0 if not health_full() else 1)
    if cmd == "repair":
        print(repair(health_full())); sys.exit(0)
    if cmd == "cycle":
        sys.exit(cycle())
    print("usage: cycle|health-full|repair")
