from types import SimpleNamespace

from runtime.transports.events import (
    TRANSPORT_RECOVERED,
    TRANSPORT_RECOVERY_FAILED,
    TRANSPORT_RESTART_REQUEST,
)
from runtime.transports.supervisor import register_transport_supervisor


class FakeBus:
    def __init__(self):
        self.subscriptions = {}
        self.events = []

    def subscribe(self, topic, callback):
        self.subscriptions.setdefault(topic, []).append(callback)

    def publish(self, topic, payload=None, source=None):
        event = SimpleNamespace(
            topic=topic,
            payload=payload or {},
            source=source,
        )
        self.events.append(event)

        for callback in self.subscriptions.get(topic, []):
            callback(event)

        return event


class MissingRegistry:
    def health(self, name):
        return {"transport": name, "running": False}

    def restart(self, name):
        raise AssertionError("restart() should not be called when transport is missing")


class FailingRegistry:
    def __init__(self):
        self.restart_calls = 0

    def health(self, name):
        return {
            "transport": name,
            "registered": True,
            "running": False,
        }

    def restart(self, name):
        self.restart_calls += 1
        raise RuntimeError(f"{name} failed to restart")


class HealthyRegistry:
    def __init__(self):
        self.restart_calls = 0

    def health(self, name):
        running = self.restart_calls > 0
        return {
            "transport": name,
            "registered": True,
            "running": running,
        }

    def restart(self, name):
        self.restart_calls += 1
        return {"transport": name, "running": True}


class FakeMetrics:
    def __init__(self):
        self.calls = []

    def increment(self, metric, value=None):
        self.calls.append((metric, value))


def test_supervisor_emits_failure_when_transport_name_missing():
    bus = FakeBus()
    registry = MissingRegistry()
    register_transport_supervisor(bus, registry)

    bus.publish(
        TRANSPORT_RESTART_REQUEST,
        {"reason": "missing transport"},
        source="Governor",
    )

    failure_events = [
        event for event in bus.events
        if event.topic == TRANSPORT_RECOVERY_FAILED
    ]
    recovered_events = [
        event for event in bus.events
        if event.topic == TRANSPORT_RECOVERED
    ]

    assert len(failure_events) == 1
    assert failure_events[0].payload["error"] == "missing transport name"
    assert failure_events[0].payload["reason"] == "missing transport"
    assert recovered_events == []


def test_supervisor_emits_failure_when_restart_raises():
    bus = FakeBus()
    registry = FailingRegistry()
    register_transport_supervisor(bus, registry)

    bus.publish(
        TRANSPORT_RESTART_REQUEST,
        {
            "transport": "clipboard",
            "reason": "transport_not_running",
        },
        source="Governor",
    )

    failure_events = [
        event for event in bus.events
        if event.topic == TRANSPORT_RECOVERY_FAILED
    ]
    recovered_events = [
        event for event in bus.events
        if event.topic == TRANSPORT_RECOVERED
    ]

    assert registry.restart_calls == 1
    assert len(failure_events) == 1
    assert failure_events[0].payload["transport"] == "clipboard"
    assert failure_events[0].payload["reason"] == "transport_not_running"
    assert "failed to restart" in failure_events[0].payload["error"]
    assert recovered_events == []


def test_supervisor_emits_recovered_and_increments_metrics():
    bus = FakeBus()
    registry = HealthyRegistry()
    metrics = FakeMetrics()
    register_transport_supervisor(bus, registry, metrics=metrics)

    bus.publish(
        TRANSPORT_RESTART_REQUEST,
        {
            "transport": "grok",
            "reason": "transport_not_running",
        },
        source="Governor",
    )

    recovered_events = [
        event for event in bus.events
        if event.topic == TRANSPORT_RECOVERED
    ]
    failure_events = [
        event for event in bus.events
        if event.topic == TRANSPORT_RECOVERY_FAILED
    ]

    assert registry.restart_calls == 1
    assert failure_events == []
    assert len(recovered_events) == 1
    assert recovered_events[0].payload["transport"] == "grok"
    assert recovered_events[0].payload["before"]["running"] is False
    assert recovered_events[0].payload["after"]["running"] is True
    assert metrics.calls == [("transport.grok.recovered", 1)]
