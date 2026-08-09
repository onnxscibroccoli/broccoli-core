"""Integration tests: real EventBus + Lifecycle + TransportRegistry through bootstrap.

Minimal stubbing only for device-bound or non-deterministic surfaces
(AccessibilityDriver capture, clipboard OS tooling).
"""
from __future__ import annotations

from types import SimpleNamespace

import runtime.bootstrap as bootstrap_mod
from runtime.eventbus.bus import EventBus
from runtime.lifecycle import (
    LIFECYCLE_COMPONENT_READY,
    LIFECYCLE_COMPONENT_STOPPED,
    LIFECYCLE_SHUTDOWN_COMPLETE,
    LIFECYCLE_SHUTDOWN_STARTED,
    LIFECYCLE_STARTUP_READY,
    LIFECYCLE_STARTUP_STARTED,
)
from runtime.transports.events import (
    TRANSPORT_HEALTH,
    TRANSPORT_RECOVERED,
    TRANSPORT_RECOVERY_FAILED,
    TRANSPORT_RESTART_REQUEST,
)


class RecordingEventBus(EventBus):
    """Real EventBus that also records published events for assertions."""

    def __init__(self):
        super().__init__()
        self.events = []

    def publish(self, topic, payload=None, source="unknown"):
        event = super().publish(topic, payload, source)
        self.events.append(event)
        return event


class SimpleTransport:
    def __init__(self, name):
        self.name = name
        self.running = False
        self.start_calls = 0
        self.stop_calls = 0

    def start(self):
        self.start_calls += 1
        self.running = True
        return self

    def stop(self):
        self.stop_calls += 1
        self.running = False
        return self

    def health(self):
        return {"running": self.running}


class FailingRestartTransport(SimpleTransport):
    def restart_fail(self):
        raise RuntimeError(f"{self.name} failed to restart")

    def start(self):
        if self.start_calls > 0:
            raise RuntimeError(f"{self.name} failed to restart")
        return super().start()


def _topics(bus: RecordingEventBus):
    return [event.topic for event in bus.events]


def _patch_device_bound(monkeypatch):
    """Stub only device-bound transports; keep registry/lifecycle/bus real."""
    monkeypatch.setattr(
        bootstrap_mod,
        "AccessibilityDriver",
        lambda bus: SimpleTransport("accessibility"),
    )
    monkeypatch.setattr(
        bootstrap_mod,
        "ClipboardEventBridge",
        lambda bus: SimpleTransport("clipboard"),
    )


def test_bootstrap_stack_emits_lifecycle_and_transport_health(monkeypatch, tmp_path):
    _patch_device_bound(monkeypatch)
    bus = RecordingEventBus()

    runtime = bootstrap_mod.build_runtime_stack(bus=bus, root=tmp_path)
    registry = runtime["transport_registry"]
    lifecycle = runtime["lifecycle"]

    # Real lifecycle over bootstrap-constructed components
    components = [
        runtime["governor"],
        runtime["accessibility"],
        runtime["planner"],
        runtime["workflow_executor"],
        runtime["grok"],
        runtime["knowledge_graph"],
        runtime["coordinator"],
        runtime["plugins"],
        runtime["transport_registry"],
    ]

    lifecycle.startup(components)
    registry.start_all()
    reports = registry.publish_health()
    health = registry.health()

    expected = {
        "accessibility",
        "clipboard",
        "grok",
        "workflow_executor",
        "adaptive_planner",
        "knowledge_graph",
        "agent_coordinator",
        "plugin_loader",
    }

    assert set(health) == expected
    assert {report["transport"] for report in reports} == expected
    assert all(report.get("running") is True for report in health.values())

    topics = _topics(bus)
    assert LIFECYCLE_STARTUP_STARTED in topics
    assert LIFECYCLE_STARTUP_READY in topics
    assert topics.count(LIFECYCLE_COMPONENT_READY) == len(components)
    assert topics.count(TRANSPORT_HEALTH) == len(expected)

    health_events = [e for e in bus.events if e.topic == TRANSPORT_HEALTH]
    assert {e.payload["transport"] for e in health_events} == expected
    assert all(e.source == "TransportRegistry" for e in health_events)

    registry.stop_all()
    lifecycle.shutdown(components)

    topics_after = _topics(bus)
    assert LIFECYCLE_SHUTDOWN_STARTED in topics_after
    assert LIFECYCLE_SHUTDOWN_COMPLETE in topics_after
    assert topics_after.count(LIFECYCLE_COMPONENT_STOPPED) == len(components)
    assert all(report.get("running") is False for report in registry.health().values())


def test_bootstrap_supervisor_emits_recovery_failed_on_restart_error(monkeypatch, tmp_path):
    _patch_device_bound(monkeypatch)
    bus = RecordingEventBus()

    runtime = bootstrap_mod.build_runtime_stack(bus=bus, root=tmp_path)
    registry = runtime["transport_registry"]

    # Replace a registered transport with one that fails on second start (restart path)
    failing = FailingRestartTransport("clipboard")
    registry.register("clipboard", failing)
    failing.start()  # first start succeeds → running True

    bus.events.clear()

    bus.publish(
        TRANSPORT_RESTART_REQUEST,
        {
            "transport": "clipboard",
            "reason": "integration_fault_injection",
        },
        source="IntegrationTest",
    )

    failures = [e for e in bus.events if e.topic == TRANSPORT_RECOVERY_FAILED]
    recovered = [e for e in bus.events if e.topic == TRANSPORT_RECOVERED]

    assert recovered == []
    assert len(failures) == 1
    assert failures[0].payload["transport"] == "clipboard"
    assert failures[0].payload["reason"] == "integration_fault_injection"
    assert "failed to restart" in failures[0].payload["error"]
    assert failures[0].source == "TransportSupervisor"
    assert failures[0].payload["before"]["running"] is True


def test_bootstrap_supervisor_emits_recovered_on_successful_restart(monkeypatch, tmp_path):
    _patch_device_bound(monkeypatch)
    bus = RecordingEventBus()

    runtime = bootstrap_mod.build_runtime_stack(bus=bus, root=tmp_path)
    registry = runtime["transport_registry"]

    target = SimpleTransport("workflow_executor")
    registry.register("workflow_executor", target)
    # Leave stopped so before.running is False

    bus.events.clear()

    bus.publish(
        TRANSPORT_RESTART_REQUEST,
        {
            "transport": "workflow_executor",
            "reason": "transport_not_running",
        },
        source="IntegrationTest",
    )

    recovered = [e for e in bus.events if e.topic == TRANSPORT_RECOVERED]
    failures = [e for e in bus.events if e.topic == TRANSPORT_RECOVERY_FAILED]

    assert failures == []
    assert len(recovered) == 1
    assert recovered[0].payload["transport"] == "workflow_executor"
    assert recovered[0].payload["before"]["running"] is False
    assert recovered[0].payload["after"]["running"] is True
    assert recovered[0].source == "TransportSupervisor"
    assert target.running is True
