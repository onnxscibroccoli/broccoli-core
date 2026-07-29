from runtime.eventbus.bus import EventBus
from runtime.transports.registry import TransportRegistry


class FakeTransport:
    def __init__(self, running=True):
        self.running = running
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1
        self.running = True
        return self

    def stop(self):
        self.stopped += 1
        self.running = False

    def health(self):
        return {
            "running": self.running,
            "poll_interval": 0.01,
            "last_digest": None,
            "last_observed_at": None,
            "last_kind": None,
        }


def test_registry_publishes_transport_health():
    bus = EventBus()
    registry = TransportRegistry(bus)
    transport = FakeTransport(running=True)
    seen = []

    bus.subscribe("TRANSPORT_HEALTH", lambda event: seen.append(event.payload))

    registry.register("clipboard", transport)
    reports = registry.publish_health()

    assert len(reports) == 1
    assert len(seen) == 1
    assert seen[0]["transport"] == "clipboard"
    assert seen[0]["running"] is True


def test_registry_restart_restarts_transport():
    bus = EventBus()
    registry = TransportRegistry(bus)
    transport = FakeTransport(running=False)

    registry.register("clipboard", transport)
    registry.restart("clipboard")

    assert transport.stopped == 1
    assert transport.started == 1
    assert transport.running is True
