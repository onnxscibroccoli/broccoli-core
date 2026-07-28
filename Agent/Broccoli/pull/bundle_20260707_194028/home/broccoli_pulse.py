
#!/usr/bin/env python3
"""Heartbeat toasts so user knows what Broccoli is doing."""
import json, subprocess, sys, time
from pathlib import Path

R = Path.home() / "broccoli"
STATE = R / "tasks" / "state.json"
WAIT = R / "reports" / "WAITING_USER.txt"
PIDF = R / "pulse.pid"

def toast(msg):
    s = ("Broccoli: " + (msg or "running"))[:110]
    subprocess.run(["termux-toast", "-s", s], timeout=6, check=False)

def phase():
    st = {}
    if STATE.is_file():
        try:
            st = json.loads(STATE.read_text())
        except Exception:
            pass
    status = st.get("status", "UNKNOWN")
    if status == "WAITING_USER":
        return "waiting for you — " + st.get("wait_label", "complete step")
    if status == "PAUSED":
        return "paused — " + (st.get("reason") or "brocc resume")
    if WAIT.is_file() and "WAITING" in WAIT.read_text(errors="replace")[:200]:
        return "waiting for user (see WAITING_USER.txt)"
    g = list((R / "inbox" / "grok").glob("*.txt"))
    gg = list((R / "inbox" / "google").glob("*.txt"))
    if g or gg:
        return "job queued — grok:%d google:%d (worker next)" % (len(g), len(gg))
    mac = R / "mac" / "inbox.jsonl"
    if mac.is_file() and mac.read_text(errors="replace").strip():
        return "mac job waiting — run mac-ingest"
    if st.get("phase") == "research":
        return "research RUNNING — idle will research round"
    return "idle — daemon watching inbox"

def loop(interval=7):
    PIDF.write_text(str(os.getpid()))
    toast(phase())
    while True:
        time.sleep(interval)
        toast(phase())

if __name__ == "__main__":
    import os
    cmd = sys.argv[1] if len(sys.argv) > 1 else "once"
    if cmd == "once":
        toast(phase()); print(phase())
    elif cmd == "loop":
        loop(int(sys.argv[2]) if len(sys.argv) > 2 else 7))
    elif cmd == "stop":
        if PIDF.is_file():
            try:
                os.kill(int(PIDF.read_text().strip()), 9)
            except Exception:
                pass
            PIDF.unlink(missing_ok=True)
        print("pulse stop")
