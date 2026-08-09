#!/usr/bin/env python3

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / ".drive_sync" / "sync.log"
PID = ROOT / ".drive_sync" / "pid"

EVENT_DIR = ROOT / "runtime" / "event_bus" / "processed"
EVENT_DIR.mkdir(parents=True, exist_ok=True)

STALL_SECONDS = 300

def publish(event, detail):
    payload = {
        "timestamp": int(time.time()),
        "event": event,
        "detail": detail
    }
    outfile = EVENT_DIR / f"sync_{int(time.time())}.json"
    outfile.write_text(json.dumps(payload, indent=2))
    print(payload)

def daemon_running():
    if not PID.exists():
        return False
    try:
        pid = PID.read_text().strip()
        subprocess.check_call(
            ["kill", "-0", pid],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception:
        return False

def restart():
    script = ROOT / "tools" / "broccoli_drive_sync_daemon.sh"
    if script.exists():
        subprocess.Popen(
            ["bash", str(script)],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        publish("SYNC_RESTARTED", "Drive sync daemon restarted")

def stalled():
    if not LOG.exists():
        return False
    age = time.time() - LOG.stat().st_mtime
    return age > STALL_SECONDS

while True:

    if not daemon_running():
        publish("SYNC_DOWN", "Daemon not running")
        restart()

    elif stalled():
        publish("SYNC_STALLED", "No log activity detected")
        restart()

    else:
        publish("SYNC_OK", "Drive sync healthy")

    time.sleep(60)
