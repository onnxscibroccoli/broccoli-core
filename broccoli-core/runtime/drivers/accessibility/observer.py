"""Continuous accessibility observation pipeline → EventBus."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import threading
import time

from .events import SemanticEvent, SemanticEventType
from .cache import SemanticCache, SemanticNode
from .diff import diff_snapshots


class AccessibilityObserver:
    """
    Phase-1 observation service.

    Flow: raw → normalize → cache upsert → diff → publish SemanticEvents.
    Falls back gracefully; does not replace snapshot path.
    """

    def __init__(self, bus=None, metrics=None, logger=None):
        self.bus = bus
        self.metrics = metrics
        self.logger = logger
        self.cache = SemanticCache()
        self._running = False
        self._lock = threading.RLock()
        self._prev_snapshot: Dict[str, Any] = {}
        self._stats = {
            "observed": 0,
            "published": 0,
            "errors": 0,
            "last_latency_ms": 0.0,
        }

    # ── lifecycle ─────────────────────────────────────────────

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._log("INFO", "AccessibilityObserver started")

    def stop(self):
        with self._lock:
            self._running = False
            self._log("INFO", "AccessibilityObserver stopped")

    def health(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "running": self._running,
                "cache_nodes": self.cache.snapshot().get("node_count", 0),
                "cache_stats": self.cache.stats(),
                "observer_stats": dict(self._stats),
            }

    # ── main entry ────────────────────────────────────────────

    def observe(self, raw_event: Dict[str, Any]) -> List[SemanticEvent]:
        """
        Accept a raw accessibility observation (dict).
        Normalize → update cache → diff → publish.
        Returns the list of SemanticEvents that were published.
        """
        if not self._running:
            return []

        t0 = time.perf_counter()
        published: List[SemanticEvent] = []
        try:
            nodes = self._normalize(raw_event)
            package = str(raw_event.get("package") or raw_event.get("packageName") or "")
            window_id = int(raw_event.get("window_id") or raw_event.get("windowId") or -1)
            screen_id = str(raw_event.get("screen_id") or raw_event.get("screenId") or "")

            self.cache.set_context(package=package, window_id=window_id, screen_id=screen_id or None)

            focused = raw_event.get("focused_id") or raw_event.get("source_id")
            if focused:
                self.cache.set_focus(str(focused))

            for node in nodes:
                self.cache.upsert(node)

            # opportunistic prune
            if self._stats["observed"] % 50 == 0:
                self.cache.prune_stale()

            curr = self.cache.snapshot()
            events = diff_snapshots(self._prev_snapshot, curr)
            self._prev_snapshot = curr

            for ev in events:
                self._publish(ev)
                published.append(ev)

            self._stats["observed"] += 1
            self._stats["published"] += len(published)
        except Exception as e:
            self._stats["errors"] += 1
            self._log("ERROR", f"observe failed: {e}")
        finally:
            latency = (time.perf_counter() - t0) * 1000.0
            self._stats["last_latency_ms"] = round(latency, 2)
            if self.metrics:
                try:
                    self.metrics.increment("a11y_observe_count")
                    self.metrics.increment("a11y_events_published", len(published))
                except Exception:
                    pass

        return published

    # ── internals ─────────────────────────────────────────────

    def _normalize(self, raw: Dict[str, Any]) -> List[SemanticNode]:
        """Turn a raw event / dump into zero-or-more SemanticNodes."""
        nodes: List[SemanticNode] = []

        # Single-node event
        if "stable_id" in raw or "id" in raw or "source_id" in raw:
            nodes.append(self._node_from_dict(raw))
            return nodes

        # Batch / tree dump
        tree = raw.get("nodes") or raw.get("tree") or raw.get("children") or []
        if isinstance(tree, dict):
            tree = list(tree.values())
        for item in tree:
            if isinstance(item, dict):
                nodes.append(self._node_from_dict(item))
        return nodes

    def _node_from_dict(self, d: Dict[str, Any]) -> SemanticNode:
        sid = str(
            d.get("stable_id")
            or d.get("id")
            or d.get("source_id")
            or d.get("viewIdResourceName")
            or f"anon_{id(d)}"
        )
        bounds = d.get("bounds") or d.get("boundsInScreen") or (0, 0, 0, 0)
        if isinstance(bounds, dict):
            bounds = (
                bounds.get("left", 0),
                bounds.get("top", 0),
                bounds.get("right", 0),
                bounds.get("bottom", 0),
            )
        return SemanticNode(
            stable_id=sid,
            class_name=str(d.get("class_name") or d.get("className") or ""),
            text=str(d.get("text") or ""),
            content_desc=str(d.get("content_desc") or d.get("contentDescription") or ""),
            bounds=tuple(bounds) if bounds else (0, 0, 0, 0),
            clickable=bool(d.get("clickable", False)),
            focused=bool(d.get("focused", False)),
            package=str(d.get("package") or d.get("packageName") or ""),
            window_id=int(d.get("window_id") or d.get("windowId") or -1),
            extras={k: v for k, v in d.items() if k not in {
                "stable_id", "id", "source_id", "class_name", "className",
                "text", "content_desc", "contentDescription", "bounds",
                "boundsInScreen", "clickable", "focused", "package",
                "packageName", "window_id", "windowId",
            }},
        )

    def _publish(self, event: SemanticEvent):
        if self.bus is None:
            return
        try:
            # Prefer publish (new), fall back to emit
            if hasattr(self.bus, "publish"):
                self.bus.publish(event.event_type.value, event.to_dict())
            elif hasattr(self.bus, "emit"):
                self.bus.emit(event.event_type.value, event.to_dict())
        except Exception as e:
            self._stats["errors"] += 1
            self._log("ERROR", f"publish failed: {e}")

    def _log(self, level: str, msg: str):
        if self.logger:
            try:
                self.logger.log(level, msg, "A11yObserver")
                return
            except Exception:
                pass
        print(f"[{level}] [A11yObserver] {msg}")
