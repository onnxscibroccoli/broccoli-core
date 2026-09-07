"""Kernel executor: search catalog and replay an authorized task."""
from __future__ import annotations

from typing import Any, Dict

from runtime.watchme.catalog import WatchCatalog


def replay_from_text(text: str) -> Dict[str, Any]:
    cat = WatchCatalog()
    q = text
    for prefix in ("run task", "run watch", "watchme run", "do task", "replay task", "replay"):
        if q.lower().startswith(prefix):
            q = q[len(prefix) :].strip()
            break
    if q.lower().startswith("do "):
        q = q[3:].strip()
    hits = cat.search(q)
    if not hits:
        return {"ok": False, "code": "no_match", "query": q}
    chosen = hits[0]
    return cat.replay(str(chosen["id"]))
