from runtime.state import RuntimeState
from runtime.eventbus import EventBus

from runtime.transports.events import (
    TRANSPORT_HEALTH,
    TRANSPORT_HEALTHY,
    TRANSPORT_RESTART_REQUEST,
    TRANSPORT_UNHEALTHY,
)


class Governor:
    def __init__(self, bus: EventBus, state):
        self.bus = bus
        self.state = state
        self._transport_recovery_requested = set()
        self.bus.subscribe("TICK", self.on_tick)
        self.bus.subscribe(TRANSPORT_HEALTH, self.on_transport_health)

    def on_tick(self, _):
        if self.state.current == "RUNNING":
            self.bus.publish("GOVERNOR_HEARTBEAT")

    def on_transport_health(self, event):
        payload = getattr(event, "payload", {}) or {}
        transport_name = payload.get("transport", "unknown")
        running = bool(payload.get("running"))

        if running:
            if transport_name in self._transport_recovery_requested:
                self.bus.publish(
                    TRANSPORT_HEALTHY,
                    payload,
                    source="Governor",
                )
            self._transport_recovery_requested.discard(transport_name)
            return

        if transport_name in self._transport_recovery_requested:
            return

        self._transport_recovery_requested.add(transport_name)
        self.bus.publish(
            TRANSPORT_UNHEALTHY,
            payload,
            source="Governor",
        )
        self.bus.publish(
            TRANSPORT_RESTART_REQUEST,
            {
                "transport": transport_name,
                "reason": "transport_not_running",
                "transport_health": payload,
            },
            source="Governor",
        )
