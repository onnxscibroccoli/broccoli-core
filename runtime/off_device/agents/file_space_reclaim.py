#!/usr/bin/env python3
"""C2: file_space_reclaim — inventory large media, propose reclaim, never delete."""
from __future__ import annotations
import json, os, sys, time, urllib.request
from pathlib import Path

SPIKE = os.environ.get("SPIKE_URL", "https://broccoli-do-spike.onnxscibroccoli.workers.dev").rstrip("/")
ROOTS = [Path.home(), Path("/sdcard"), Path("/storage/emulated/0")]
EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".mp3", ".flac", ".iso"}
MIN_BYTES = 50 * 1024 * 1024  # 50 MiB

def http(method, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        SPIKE + path, data=data, method=method,
        headers={"content-type": "application/json", "accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def scan():
    hits = []
    for root in ROOTS:
        if not root.exists():
            continue
        try:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                # skip noise
                dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules", ".cache"}]
                for name in filenames:
                    path = Path(dirpath) / name
                    if path.suffix.lower() not in EXTS:
                        continue
                    try:
                        st = path.stat()
                    except OSError:
                        continue
                    if st.st_size < MIN_BYTES:
                        continue
                    hits.append({"path": str(path), "bytes": st.st_size, "ext": path.suffix.lower()})
        except OSError:
            continue
    hits.sort(key=lambda x: -x["bytes"])
    return hits[:200]

def main():
    hits = scan()
    total = sum(h["bytes"] for h in hits)
    goal = f"Propose reclaim of {len(hits)} large media files (\~{total//(1024*1024)} MiB); human confirm deletes"
    t = http("POST", "/task", {"goal": goal, "domain": "file_space_reclaim", "status": "running"})
    task = t["task"]
    tid = task["id"]
    proposal = {
        "task_id": tid,
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "min_bytes": MIN_BYTES,
        "count": len(hits),
        "total_bytes": total,
        "candidates": hits,
        "policy": "suggest only; no deletes without needs_user confirm",
    }
    http("POST", "/write", {"path": f"proposals/{tid}.json", "content": json.dumps(proposal, indent=2)})
    http("PATCH", "/task", {
        "id": tid,
        "status": "needs_user",
        "notes": "Review candidates; confirm before any delete",
        "artifacts": [{"path": f"/workspace/proposals/{tid}.json", "kind": "proposal"}],
    })
    http("POST", "/receipt", {
        "id": tid,
        "summary": f"Found {len(hits)} files totaling {total//(1024*1024)} MiB. Awaiting user confirm.",
    })
    print(json.dumps({"ok": True, "task_id": tid, "count": len(hits), "total_mib": total//(1024*1024)}, indent=2))

if __name__ == "__main__":
    main()
