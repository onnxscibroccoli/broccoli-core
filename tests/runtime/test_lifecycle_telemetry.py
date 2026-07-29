from runtime.lifecycle import (
    LIFECYCLE_COMPONENT_READY,
    LIFECYCLE_COMPONENT_STOPPED,
    LIFECYCLE_SHUTDOWN_COMPLETE,
    LIFECYCLE_SHUTDOWN_STARTED,
    LIFECYCLE_STARTUP_READY,
    LIFECYCLE_STARTUP_STARTED,
    Lifecycle,
)


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, topic, payload=None, source=None):
        event = {
            "topic": topic,
            "payload": payload or {},
            "source": source,
        }
        self.events.append(event)
        return event


class AlphaComponent:
    pass


class BetaComponent:
    pass


def test_lifecycle_emits_startup_and_shutdown_telemetry():
    bus = FakeBus()
    lifecycle = Lifecycle(bus)
    components = [AlphaComponent(), BetaComponent()]

    lifecycle.startup(components)
    lifecycle.shutdown(components)

    topics = [event["topic"] for event in bus.events]

    assert topics == [
        LIFECYCLE_STARTUP_STARTED,
        LIFECYCLE_COMPONENT_READY,
        LIFECYCLE_COMPONENT_READY,
        LIFECYCLE_STARTUP_READY,
        LIFECYCLE_SHUTDOWN_STARTED,
        LIFECYCLE_COMPONENT_STOPPED,
        LIFECYCLE_COMPONENT_STOPPED,
        LIFECYCLE_SHUTDOWN_COMPLETE,
    ]

    assert bus.events[1]["payload"]["component"] == "AlphaComponent"
    assert bus.events[2]["payload"]["component"] == "BetaComponent"
    assert bus.events[5]["payload"]["component"] == "BetaComponent"
    assert bus.events[6]["payload"]["component"] == "AlphaComponent"
    assert bus.events[0]["source"] == "Lifecycle"
    assert bus.events[-1]["source"] == "Lifecycle"
