from runtime.state import RuntimeState
from runtime.eventbus import EventBus

from runtime.clipboard.events import (
    CLIPBOARD_BRIDGE_HEALTH,
    CLIPBOARD_BRIDGE_HEALTHY,
    CLIPBOARD_BRIDGE_RESTART_REQUEST,
    CLIPBOARD_BRIDGE_UNHEALTHY,
)

class Governor:
    def __init__(self, bus: EventBus, state):
        self.bus = bus
        self.state = state
        self._clipboard_bridge_recovery_requested = False
        self.bus.subscribe("TICK", self.on_tick)
        self.bus.subscribe(CLIPBOARD_BRIDGE_HEALTH, self.on_clipboard_bridge_health)

    def on_tick(self, _):
        if self.state.current == "RUNNING":
            self.bus.publish("GOVERNOR_HEARTBEAT")

    def on_clipboard_bridge_health(self, event):
        payload = getattr(event, "payload", {}) or {}
        running = bool(payload.get("running"))

        if running:
            if self._clipboard_bridge_recovery_requested:
                self.bus.publish(
                    CLIPBOARD_BRIDGE_HEALTHY,
                    payload,
                    source="Governor",
                )
            self._clipboard_bridge_recovery_requested = False
            return

        if self._clipboard_bridge_recovery_requested:
            return

        self._clipboard_bridge_recovery_requested = True
        self.bus.publish(
            CLIPBOARD_BRIDGE_UNHEALTHY,
            payload,
            source="Governor",
        )
        self.bus.publish(
            CLIPBOARD_BRIDGE_RESTART_REQUEST,
            {
                "reason": "bridge_not_running",
                "bridge_health": payload,
            },
            source="Governor",
        )
