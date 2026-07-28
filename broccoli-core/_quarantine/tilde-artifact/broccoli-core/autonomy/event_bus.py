#!/usr/bin/env python3
"""
Minimal in-process EventBus for Broccoli Core.

- Synchronous publish/subscribe
- Thread-safe
- Optional persistent ring-buffer log (last N events)
- Zero external dependencies
"""

import logging
import time
import threading
from collections import defaultdict, deque
from typing import Callable, Dict, List, Any, Optional, Deque

class EventBus:
    def __init__(self, history_size: int = 200):
        self.logger = logging.getLogger("broccoli.event_bus")
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()
        self._history: Deque[Dict[str, Any]] = deque(maxlen=history_size)

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback for a specific event type (or '*' for all)."""
        with self._lock:
            self._subscribers[event_type].append(callback)
            self.logger.debug(f"Subscribed to {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def emit(self, event_type: str, payload: Optional[Dict[str, Any]] = None):
        """Publish an event. Payload is passed to every matching subscriber."""
        payload = payload or {}
        event = {
            "type": event_type,
            "payload": payload,
            "timestamp": time.time()
        }

        with self._lock:
            self._history.append(event)
            # specific listeners
            listeners = list(self._subscribers.get(event_type, []))
            # wildcard listeners
            listeners.extend(self._subscribers.get("*", []))

        for cb in listeners:
            try:
                cb(event)
            except Exception as e:
                self.logger.error(f"Listener error on {event_type}: {e}")

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        with self._lock:
            if event_type is None:
                return list(self._history)[-limit:]
            return [e for e in self._history if e["type"] == event_type][-limit:]

    def clear_history(self):
        with self._lock:
            self._history.clear()


# ── self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    bus = EventBus()

    received = []
    def on_any(event):
        received.append(event["type"])
        print(f"  → caught {event['type']}")

    bus.subscribe("*", on_any)
    bus.subscribe("GOAL_COMPLETED", lambda e: print(f"  ★ COMPLETED payload: {e['payload']}"))

    bus.emit("GOAL_CREATED", {"goal_id": "abc", "name": "demo"})
    bus.emit("GOAL_COMPLETED", {"goal_id": "abc"})

    assert "GOAL_CREATED" in received
    assert "GOAL_COMPLETED" in received
    print("✅ EventBus self-test passed")
    print(f"History size: {len(bus.get_history())}")
