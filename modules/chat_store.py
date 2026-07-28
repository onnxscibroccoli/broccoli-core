#!/usr/bin/env python3
import json, os, time, hashlib

def thread_id(state: dict, tail: str) -> str:
    key = (state.get("fg_package") or "") + "|" + (tail[:200] if tail else "empty")
    return hashlib.sha256(key.encode()).hexdigest()[:16]

def save(root: str, state: dict, payload: dict) -> str:
    os.makedirs(os.path.join(root, "data", "harvest"), exist_ok=True)
    tid = thread_id(state, payload.get("tail", ""))
    rec = {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "thread_id": tid,
        "state": {k: state.get(k) for k in ("fg_package", "on_grok", "screen", "input_xy", "new_chat_focused")},
        "line_count": payload.get("line_count", 0),
        "tail": payload.get("tail", ""),
        "lines": payload.get("lines", [])[-80:],
    }
    path = os.path.join(root, "data", "harvest", f"{tid}.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    latest = os.path.join(root, "data", "harvest", "latest.json")
    open(latest, "w", encoding="utf-8").write(json.dumps(rec, indent=2, ensure_ascii=False))
    return path

def precondition(state: dict) -> tuple[bool, str]:
    return True, "ok"

def run(ctx) -> "ModuleResult":
    from modules.registry import ModuleResult
    payload = ctx.env.get("_reader_payload") or {}
    if not payload.get("tail") and not payload.get("lines"):
        return ModuleResult(False, "chat_store", reason="empty_payload")
    path = save(ctx.root, ctx.state, payload)
    return ModuleResult(True, "chat_store", data={"path": path})

# ---- Compatibility wrapper added automatically ----
def harvest_payload(*args, **kwargs):
    """
    Backwards-compatible wrapper.
    Replace this implementation with the native one when available.
    """
    try:
        if 'harvest' in globals():
            return harvest(*args, **kwargs)
        if 'store_payload' in globals():
            return store_payload(*args, **kwargs)
        return None
    except Exception:
        return None
