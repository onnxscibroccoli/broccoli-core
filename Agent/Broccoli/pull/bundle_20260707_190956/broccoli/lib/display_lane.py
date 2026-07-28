"""Secondary lane: user keeps phone; automation when idle or forced."""
import json, time, re
from pathlib import Path

HOME = Path.home()
POLICY = HOME / "broccoli/meta/display_policy.json"
TOUCH_RING = HOME / "broccoli/godmode/buffer/touch_ring.jsonl"
QUEUE = HOME / "broccoli/meta/deferred_jobs.jsonl"
DEFAULT = {"mode": "user_primary", "idle_seconds": 8}

def load_policy():
    if POLICY.exists():
        try:
            return {**DEFAULT, **json.loads(POLICY.read_text())}
        except Exception:
            pass
    POLICY.parent.mkdir(parents=True, exist_ok=True)
    POLICY.write_text(json.dumps({**DEFAULT, "mode": "user_primary"}, indent=2))
    return dict(DEFAULT)

def last_user_touch_ts():
    if not TOUCH_RING.exists():
        return 0.0
    last = 0.0
    for line in TOUCH_RING.read_text(errors="replace").splitlines()[-300:]:
        try:
            ev = json.loads(line)
            if ev.get("meta", {}).get("origin") != "bootstrap":
                last = max(last, float(ev.get("ts", 0)))
        except Exception:
            pass
    return last

def user_is_idle(idle_seconds=None):
    p = load_policy()
    sec = idle_seconds if idle_seconds is not None else float(p.get("idle_seconds", 8))
    return (time.time() - last_user_touch_ts()) >= sec

def may_run_foreground_ui():
    p = load_policy()
    if p.get("mode") == "automation_secondary":
        return True
    if p.get("force_secondary"):
        return True
    return user_is_idle()

def enqueue_deferred(job_type, payload=None):
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    rec = {"ts": time.time(), "type": job_type, "payload": payload or {}}
    with QUEUE.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec

def enable_user_primary(idle_seconds=8):
    p = load_policy()
    p["mode"] = "user_primary"
    p["idle_seconds"] = idle_seconds
    p["force_secondary"] = False
    POLICY.write_text(json.dumps(p, indent=2))
    return p

def enable_automation_secondary():
    p = load_policy()
    p["mode"] = "automation_secondary"
    POLICY.write_text(json.dumps(p, indent=2))
    return p
