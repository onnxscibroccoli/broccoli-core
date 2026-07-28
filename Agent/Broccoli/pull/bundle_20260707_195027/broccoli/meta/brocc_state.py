
#!/usr/bin/env python3
import json, hashlib, time, sys
from pathlib import Path
STATE = Path.home() / "broccoli/meta/loop_state.json"
DEFAULT = {"phase": "await_grok", "last_emit_hash": "", "last_emit_ts": 0, "last_fingerprint": "", "emit_min_interval_sec": 90}

def load():
    return {**DEFAULT, **json.loads(STATE.read_text())} if STATE.is_file() else dict(DEFAULT)

def save(d):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, indent=2))

def set_phase(p):
    d = load(); d["phase"] = p; save(d)

def should_emit(report, fp):
    d, now = load(), time.time()
    if d["phase"] != "await_grok": return False
    if now - d["last_emit_ts"] < d["emit_min_interval_sec"] and report.get("missing", 0) == 0 and report.get("stale", 0) == 0:
        return False
    body = json.dumps(report, sort_keys=True)
    h = hashlib.sha256(body.encode()).hexdigest()
    if fp == d["last_fingerprint"] and h == d["last_emit_hash"]: return False
    return True

def mark_emit(report, fp):
    d = load()
    d["last_emit_hash"] = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    d["last_emit_ts"] = time.time()
    d["last_fingerprint"] = fp
    save(d)

if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "set_phase":
        set_phase(sys.argv[2])
