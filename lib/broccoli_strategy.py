import json, time
from pathlib import Path

BRO = Path.home() / "broccoli"
PATHS = BRO / "meta/working_paths.json"
LOG = BRO / "reports/strategy.log"

def _load():
    if PATHS.exists():
        try:
            return json.loads(PATHS.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"send": [], "inject": [], "recv": []}

def log_path(kind, method, ok, extra=None):
    d = _load()
    d.setdefault(kind, [])
    entry = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "method": method, "ok": ok}
    if extra: entry.update(extra)
    d[kind].insert(0, entry)
    d[kind] = d[kind][:30]
    PATHS.write_text(json.dumps(d, indent=2), encoding="utf-8")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    prev = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
    LOG.write_text(prev + json.dumps(entry) + "\n", encoding="utf-8")

def best_send_method():
    d = _load()
    for e in d.get("send", []):
        if e.get("ok"):
            return e.get("method")
    return None
