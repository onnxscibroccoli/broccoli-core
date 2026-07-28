#!/usr/bin/env python3
"""Stop daemons, clear stale locks, verify bootstrap, warm Shizuku path."""
import subprocess, time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "broccoli"
REP = ROOT / "reports"

def run(cmd, t=30):
    print("REBOOT", cmd, flush=True)
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    except Exception as e:
        return type("R", (), {"stdout": "", "stderr": str(e), "returncode": -1})()

def toast(msg):
    subprocess.run(["termux-toast", "-g", "bottom", msg[:100]], timeout=6, capture_output=True)

def main():
    toast("Reboot bootstrap")
    run("pkill -f daemon_idle_loop 2>/dev/null; pkill -f broccoli-daemon 2>/dev/null; true")
    run("brocc stop 2>/dev/null; true")
    time.sleep(1)
    for lock in (ROOT / "meta" / "worker.lock", ROOT / "ui" / "busy.flag"):
        lock.unlink(missing_ok=True)
    boot = HOME / "broccoli_bootstrap.py"
    ok = boot.is_file()
    (REP / "reboot_bootstrap.txt").write_text(
        f"bootstrap_exists={ok}\nbootstrap={boot}\n"
    )
    if ok:
        run(f'python3 "{boot}" --help 2>&1 | head -5 || python3 "{boot}" 2>&1 | head -3', 25)
    toast("Bootstrap rebooted")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
