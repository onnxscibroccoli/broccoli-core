"""Broccoli task queue log — durable across daemon iterations."""
import json, time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "broccoli"
META, REP = ROOT / "meta", ROOT / "reports"
LOG = META / "task_queue.jsonl"
SNAP = META / "task_queue_snapshot.json"
CTX = REP / "task_queue_context.txt"
PASTE = REP / "task_queue_paste_block.txt"

def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def log_event(kind, task="", detail="", status="", extra=None):
    """kind: queued|started|done|failed|skipped|note|front|smoke|user"""
    META.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": time.time(),
        "ts_human": _now(),
        "kind": kind,
        "task": (task or "")[:200],
        "detail": (detail or "")[:500],
        "status": status or "",
    }
    if extra and isinstance(extra, dict):
        row.update({k: v for k, v in extra.items() if k not in row})
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    _refresh_snapshot(row)
    rebuild_context()
    return row

def _read_tail(n=80):
    if not LOG.exists():
        return []
    lines = LOG.read_text(errors="replace").strip().splitlines()
    out = []
    for line in lines[-n:]:
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out

def _refresh_snapshot(last_row=None):
    tail = _read_tail(200)
    pending, active, recent_done, recent_fail = [], None, [], []
    for r in tail:
        k, t = r.get("kind"), r.get("task") or "(no name)"
        if k == "queued":
            pending.append({"task": t, "ts": r.get("ts_human"), "detail": r.get("detail", "")})
        elif k == "started":
            active = {"task": t, "ts": r.get("ts_human"), "detail": r.get("detail", "")}
            pending = [p for p in pending if p.get("task") != t]
        elif k == "done":
            recent_done.insert(0, {"task": t, "ts": r.get("ts_human"), "status": r.get("status", "ok")})
            if active and active.get("task") == t:
                active = None
        elif k == "failed":
            recent_fail.insert(0, {"task": t, "ts": r.get("ts_human"), "detail": r.get("detail", "")})
            if active and active.get("task") == t:
                active = None
    snap = {
        "updated_at": time.time(),
        "updated_human": _now(),
        "active": active,
        "pending": pending[-20:],
        "recent_done": recent_done[:15],
        "recent_failed": recent_fail[:10],
        "last_event": last_row or (tail[-1] if tail else None),
    }
    SNAP.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return snap

def rebuild_context(max_lines=40):
    snap = json.loads(SNAP.read_text()) if SNAP.exists() else _refresh_snapshot()
    tail = _read_tail(max_lines)
    lines = [
        "=== BROCCOLI TASK QUEUE (auto-generated) ===",
        f"Updated: {snap.get('updated_human', '?')}",
        "",
    ]
    if snap.get("active"):
        a = snap["active"]
        lines.append(f"ACTIVE: {a.get('task')} (since {a.get('ts')})")
    else:
        lines.append("ACTIVE: (none)")
    lines.append("")
    pend = snap.get("pending") or []
    lines.append(f"PENDING ({len(pend)}):")
    for i, p in enumerate(pend, 1):
        lines.append(f"  {i}. {p.get('task')} — {p.get('detail', '')[:80]}")
    if not pend:
        lines.append("  (empty)")
    lines.append("")
    lines.append("RECENT DONE:")
    for d in (snap.get("recent_done") or [])[:8]:
        lines.append(f"  ✓ {d.get('task')} @ {d.get('ts')}")
    lines.append("")
    lines.append("RECENT FAILED:")
    for f in (snap.get("recent_failed") or [])[:5]:
        lines.append(f"  ✗ {f.get('task')} @ {f.get('ts')} — {str(f.get('detail', ''))[:60]}")
    lines.append("")
    lines.append("LAST ITERATION (tail):")
    for r in tail[-12:]:
        lines.append(f"  [{r.get('ts_human')}] {r.get('kind')}: {r.get('task') or '-'} {r.get('detail', '')[:50]}")
    lines.append("=== END TASK QUEUE ===")
    text = "\n".join(lines)
    CTX.write_text(text, encoding="utf-8")
    paste = (
        "When the user asks about the Broccoli task queue, workflow, or what is running, "
        "use ONLY this snapshot (do not invent tasks):\n\n" + text
    )
    PASTE.write_text(paste, encoding="utf-8")
    return text

def enqueue(task, detail=""):
    return log_event("queued", task=task, detail=detail)

def started(task, detail=""):
    return log_event("started", task=task, detail=detail)

def done(task, detail="", status="ok"):
    return log_event("done", task=task, detail=detail, status=status)

def failed(task, detail=""):
    return log_event("failed", task=task, detail=detail, status="fail")

def note(detail):
    return log_event("note", task="system", detail=detail)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(rebuild_context())
        raise SystemExit(0)
    cmd = sys.argv[1]
    if cmd == "show":
        print(rebuild_context())
    elif cmd == "paste":
        print((REP / "task_queue_paste_block.txt").read_text(errors="replace"))
    elif cmd == "enqueue" and len(sys.argv) > 2:
        print(json.dumps(enqueue(" ".join(sys.argv[2:])), indent=2))
    else:
        print("usage: task_queue.py show|paste|enqueue <task>")
