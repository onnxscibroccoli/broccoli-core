from runtime.eventbus.bus import EventBus
from runtime.transports.registry import TransportRegistry
from runtime.transports.supervisor import register_transport_supervisor


class FakeTransport:
    def __init__(self):
        self.started = 0
        self.stopped = 0
        self.running = False

    def health(self):
        return {
            "running": self.running,
            "poll_interval": 0.01,
            "last_digest": None,
            "last_observed_at": None,
            "last_kind": None,
        }

    def stop(self):
        self.stopped += 1
        self.running = False

    def start(self):
        self.started += 1
        self.running = True
        return self


def test_transport_supervisor_restarts_transport_and_emits_recovery():
    bus = EventBus()
    registry = TransportRegistry(bus)
    transport = FakeTransport()
    registry.register("clipboard", transport)

    recovered = []
    failed = []

    bus.subscribe("TRANSPORT_RECOVERED", lambda event: recovered.append(event.payload))
    bus.subscribe("TRANSPORT_RECOVERY_FAILED", lambda event: failed.append(event.payload))

    register_transport_supervisor(bus, registry)

    bus.publish(
        "TRANSPORT_RESTART_REQUEST",
        {
            "transport": "clipboard",
            "reason": "transport_not_running",
        },
        source="Governor",
    )

    assert transport.stopped == 1
    assert transport.started == 1
    assert failed == []
    assert len(recovered) == 1
    assert recovered[0]["after"]["running"] is True
