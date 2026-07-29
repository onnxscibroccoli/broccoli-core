from types import SimpleNamespace

import runtime.main as main_mod
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

    def subscribe(self, *args, **kwargs):
        return None

    def publish(self, topic, payload=None, source=None):
        event = {
            "topic": topic,
            "payload": payload or {},
            "source": source,
        }
        self.events.append(event)
        return event


class FakeLogger:
    def __init__(self):
        self.calls = []

    def log(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return None


class FakeState:
    def __init__(self):
        self.current = "INITIALIZING"
        self.transitions = []

    def transition(self, state):
        self.current = state
        self.transitions.append(state)


class FakeMetrics:
    def __init__(self):
        self.calls = []

    def increment(self, metric, value=None):
        self.calls.append((metric, value))
        return None


class FakeScheduler:
    def __init__(self):
        self.run_calls = 0

    def run_pending(self):
        self.run_calls += 1
        return None


class FakeHealthMonitor:
    def __init__(self):
        self.check_calls = 0

    def check(self):
        self.check_calls += 1
        return {"healthy": True}


class FakeWorkflowExecutor:
    def __init__(self):
        self.run_calls = 0

    def run_pending(self):
        self.run_calls += 1
        return None


class FakeRecoveryManager:
    def __init__(self):
        self.scan_calls = 0

    def scan_and_recover(self):
        self.scan_calls += 1
        return 1


class FakeGoalManager:
    def __init__(self):
        self.created = []

    def create_goal(self, goal_id, goal_text):
        self.created.append((goal_id, goal_text))
        return None


class FakeTransportRegistry:
    def __init__(self, bus):
        self.bus = bus
        self.start_all_calls = 0
        self.publish_health_calls = 0
        self.stop_all_calls = 0

    def start_all(self):
        self.start_all_calls += 1

    def publish_health(self):
        self.publish_health_calls += 1
        self.bus.publish(
            "TRANSPORT_HEALTH",
            {"transport": "bootstrap", "running": True},
            source="TransportRegistry",
        )
        return [{"transport": "bootstrap", "running": True}]

    def stop_all(self):
        self.stop_all_calls += 1


class FakeConfig:
    def load(self):
        return SimpleNamespace(tick_seconds=0.0)


class DummyComponent:
    pass


def test_runtime_main_emits_lifecycle_and_shutdown(monkeypatch):
    bus = FakeBus()
    runtime = {
        "bus": bus,
        "config": FakeConfig().load(),
        "logger": FakeLogger(),
        "state": FakeState(),
        "metrics": FakeMetrics(),
        "scheduler": FakeScheduler(),
        "health": FakeHealthMonitor(),
        "lifecycle": Lifecycle(bus),
        "workflow_executor": FakeWorkflowExecutor(),
        "recovery": FakeRecoveryManager(),
        "goal_manager": FakeGoalManager(),
        "transport_registry": FakeTransportRegistry(bus),
        "governor": DummyComponent(),
        "accessibility": DummyComponent(),
        "planner": DummyComponent(),
        "grok": DummyComponent(),
        "knowledge_graph": DummyComponent(),
        "knowledge_graph_transport": DummyComponent(),
        "coordinator": DummyComponent(),
        "plugins": DummyComponent(),
        "plugin_loader_transport": DummyComponent(),
    }

    monkeypatch.setattr(main_mod, "build_runtime_stack", lambda: runtime)
    monkeypatch.setattr(main_mod, "RECOVERY_SCAN_EVERY", 1)

    def fake_sleep(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr(main_mod.time, "sleep", fake_sleep)

    main_mod.main()

    topics = [event["topic"] for event in bus.events]

    assert topics.count(LIFECYCLE_STARTUP_STARTED) == 1
    assert topics.count(LIFECYCLE_STARTUP_READY) == 1
    assert topics.count(LIFECYCLE_SHUTDOWN_STARTED) == 1
    assert topics.count(LIFECYCLE_SHUTDOWN_COMPLETE) == 1
    assert topics.count(LIFECYCLE_COMPONENT_READY) >= 1
    assert topics.count(LIFECYCLE_COMPONENT_STOPPED) >= 1
    assert "TICK" in topics
    assert "HEALTH_CHECK" in topics
    assert "TRANSPORT_HEALTH" in topics

    assert runtime["state"].transitions == ["RUNNING", "STOPPED"]
    assert runtime["transport_registry"].start_all_calls == 1
    assert runtime["transport_registry"].publish_health_calls == 1
    assert runtime["transport_registry"].stop_all_calls == 1
    assert runtime["scheduler"].run_calls == 1
    assert runtime["workflow_executor"].run_calls == 1
    assert runtime["health"].check_calls == 1
    assert runtime["metrics"].calls == [("loop_cycles", None)]
    assert runtime["recovery"].scan_calls == 1
    assert runtime["goal_manager"].created == [("test_goal", "Test autonomous task")]
