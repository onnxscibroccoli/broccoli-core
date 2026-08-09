from __future__ import annotations

from typing import Any, Iterable, Optional

LIFECYCLE_STARTUP_STARTED = "LIFECYCLE_STARTUP_STARTED"
LIFECYCLE_COMPONENT_READY = "LIFECYCLE_COMPONENT_READY"
LIFECYCLE_STARTUP_READY = "LIFECYCLE_STARTUP_READY"
LIFECYCLE_SHUTDOWN_STARTED = "LIFECYCLE_SHUTDOWN_STARTED"
LIFECYCLE_COMPONENT_STOPPED = "LIFECYCLE_COMPONENT_STOPPED"
LIFECYCLE_SHUTDOWN_COMPLETE = "LIFECYCLE_SHUTDOWN_COMPLETE"


class Lifecycle:
    def __init__(self, bus=None):
        self.bus = bus

    def _publish(self, topic: str, payload: dict) -> None:
        if self.bus and hasattr(self.bus, "publish"):
            try:
                self.bus.publish(topic, payload, source="Lifecycle")
            except Exception:
                pass

    def startup(self, components: Iterable[Any]):
        items = list(components)
        total = len(items)

        print("Runtime starting...")
        self._publish(LIFECYCLE_STARTUP_STARTED, {"count": total})

        for index, component in enumerate(items, start=1):
            name = component.__class__.__name__
            print(f"  ✓ {name}")
            self._publish(
                LIFECYCLE_COMPONENT_READY,
                {
                    "component": name,
                    "index": index,
                    "count": total,
                },
            )

        print("Runtime READY")
        self._publish(LIFECYCLE_STARTUP_READY, {"count": total})

    def shutdown(self, components: Optional[Iterable[Any]] = None):
        items = list(components or [])
        total = len(items)

        print("Runtime stopping...")
        self._publish(LIFECYCLE_SHUTDOWN_STARTED, {"count": total})

        for index, component in enumerate(reversed(items), start=1):
            name = component.__class__.__name__
            print(f"  ✓ {name}")
            self._publish(
                LIFECYCLE_COMPONENT_STOPPED,
                {
                    "component": name,
                    "index": index,
                    "count": total,
                },
            )

        print("Runtime STOPPED")
        self._publish(LIFECYCLE_SHUTDOWN_COMPLETE, {"count": total})
