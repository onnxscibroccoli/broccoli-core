"""Auto-update current task from queue + chat."""
import json, time
from pathlib import Path

ROOT = Path.home() / "broccoli"
META, REP = ROOT / "meta", ROOT / "reports"
CURRENT = META / "current_task.json"
QUEUE_SNAP = META / "task_queue_snapshot.json"

def load_current():
    if CURRENT.exists():
        try:
            return json.loads(CURRENT.read_text())
        except Exception:
            pass
    return {"task": "", "status": "idle", "round": 0, "history": []}

def save_current(data):
    META.mkdir(parents=True, exist_ok=True)
    CURRENT.write_text(json.dumps(data, indent=2), encoding="utf-8")

def sync_from_queue():
    """Pick active or first pending as current task."""
    data = load_current()
    if QUEUE_SNAP.exists():
        try:
            snap = json.loads(QUEUE_SNAP.read_text())
            if snap.get("active"):
                data["task"] = snap["active"].get("task", data.get("task", ""))
                data["status"] = "active"
            elif snap.get("pending"):
                data["task"] = snap["pending"][0].get("task", "")
                data["status"] = "pending"
        except Exception:
            pass
    save_current(data)
    return data

def start_task(name, detail=""):
    data = load_current()
    data["task"] = name
    data["status"] = "running"
    data["started_at"] = time.time()
    data["detail"] = detail
    data["round"] = int(data.get("round", 0)) + 1
    save_current(data)
    try:
        import sys
        sys.path.insert(0, str(ROOT / "lib"))
        from task_queue import started, rebuild_context
        started(name, detail=detail or "recursive_impl")
        rebuild_context()
    except Exception:
        pass
    return data

def complete_task(name, ok=True, detail=""):
    data = load_current()
    data["status"] = "done" if ok else "failed"
    data["finished_at"] = time.time()
    data["last_result"] = detail[:500]
    hist = data.get("history", [])
    hist.append({"task": name, "ok": ok, "detail": detail[:200], "at": time.time()})
    data["history"] = hist[-30:]
    save_current(data)
    try:
        import sys
        sys.path.insert(0, str(ROOT / "lib"))
        from task_queue import done, failed, note, rebuild_context
        (done if ok else failed)(name, detail=detail)
        note(f"recursive: {name} {'PASS' if ok else 'FAIL'}")
        rebuild_context()
    except Exception:
        pass
    return data

def infer_task_from_reply(text):
    """If Grok names a task in reply, update current."""
    if not text:
        return None
    for pat in (
        r"(?i)current task[:\s]+([^\n.]+)",
        r"(?i)next[:\s]+implement[:\s]+([^\n.]+)",
        r"(?i)TASK[:\s]+([A-Z0-9_ -]{4,40})",
    ):
        import re
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return None

def update_from_chat_reply(reply_text):
    data = load_current()
    inferred = infer_task_from_reply(reply_text)
    if inferred:
        data["task"] = inferred
        data["status"] = "running"
    data["last_reply_snip"] = (reply_text or "")[:400]
    save_current(data)
    return data
