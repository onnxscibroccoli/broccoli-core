"""Thread-safe incremental semantic UI state cache."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import threading
import time
from collections import deque


@dataclass
class SemanticNode:
    stable_id: str
    class_name: str = ""
    text: str = ""
    content_desc: str = ""
    bounds: tuple = (0, 0, 0, 0)   # l, t, r, b
    clickable: bool = False
    focused: bool = False
    package: str = ""
    window_id: int = -1
    extras: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def fingerprint(self) -> str:
        """Cheap change detector."""
        return f"{self.text}|{self.content_desc}|{self.bounds}|{self.focused}|{self.clickable}"


class SemanticCache:
    """Incremental semantic node map with bounded history."""

    def __init__(self, max_history: int = 32, stale_seconds: float = 120.0):
        self._lock = threading.RLock()
        self._nodes: Dict[str, SemanticNode] = {}
        self._focused_id: Optional[str] = None
        self._package: str = ""
        self._window_id: int = -1
        self._screen_id: str = ""
        self._last_update: float = 0.0
        self._history: deque = deque(maxlen=max_history)
        self._stale_seconds = stale_seconds
        self._stats = {
            "inserts": 0,
            "updates": 0,
            "removes": 0,
            "prunes": 0,
            "snapshots": 0,
        }

    # ── mutation ──────────────────────────────────────────────

    def upsert(self, node: SemanticNode) -> str:
        """Insert or update. Returns 'inserted' | 'updated' | 'unchanged'."""
        with self._lock:
            existing = self._nodes.get(node.stable_id)
            node.updated_at = time.time()
            self._last_update = node.updated_at
            if existing is None:
                self._nodes[node.stable_id] = node
                self._stats["inserts"] += 1
                self._history.append(("insert", node.stable_id, node.updated_at))
                return "inserted"
            if existing.fingerprint() != node.fingerprint():
                self._nodes[node.stable_id] = node
                self._stats["updates"] += 1
                self._history.append(("update", node.stable_id, node.updated_at))
                return "updated"
            # touch timestamp only
            existing.updated_at = node.updated_at
            return "unchanged"

    def remove(self, stable_id: str) -> bool:
        with self._lock:
            if stable_id in self._nodes:
                del self._nodes[stable_id]
                if self._focused_id == stable_id:
                    self._focused_id = None
                self._stats["removes"] += 1
                self._history.append(("remove", stable_id, time.time()))
                return True
            return False

    def set_focus(self, stable_id: Optional[str]):
        with self._lock:
            self._focused_id = stable_id
            self._last_update = time.time()

    def set_context(self, package: str = None, window_id: int = None, screen_id: str = None):
        with self._lock:
            if package is not None:
                self._package = package
            if window_id is not None:
                self._window_id = window_id
            if screen_id is not None:
                self._screen_id = screen_id
            self._last_update = time.time()

    def prune_stale(self) -> int:
        cutoff = time.time() - self._stale_seconds
        with self._lock:
            stale = [sid for sid, n in self._nodes.items() if n.updated_at < cutoff]
            for sid in stale:
                del self._nodes[sid]
                if self._focused_id == sid:
                    self._focused_id = None
            self._stats["prunes"] += len(stale)
            return len(stale)

    # ── query ─────────────────────────────────────────────────

    def get(self, stable_id: str) -> Optional[SemanticNode]:
        with self._lock:
            return self._nodes.get(stable_id)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            self._stats["snapshots"] += 1
            return {
                "nodes": {sid: {
                    "stable_id": n.stable_id,
                    "class_name": n.class_name,
                    "text": n.text,
                    "content_desc": n.content_desc,
                    "bounds": n.bounds,
                    "clickable": n.clickable,
                    "focused": n.focused,
                    "package": n.package,
                    "window_id": n.window_id,
                    "extras": dict(n.extras),
                    "updated_at": n.updated_at,
                    "fingerprint": n.fingerprint(),
                } for sid, n in self._nodes.items()},
                "focused_id": self._focused_id,
                "package": self._package,
                "window_id": self._window_id,
                "screen_id": self._screen_id,
                "last_update": self._last_update,
                "node_count": len(self._nodes),
            }

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._stats)

    def clear(self):
        with self._lock:
            self._nodes.clear()
            self._focused_id = None
            self._history.clear()
            self._last_update = time.time()
