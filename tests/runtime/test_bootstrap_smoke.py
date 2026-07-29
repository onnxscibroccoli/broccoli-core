from types import SimpleNamespace

from runtime import bootstrap as bootstrap_mod


class FakeBus:
    def __init__(self):
        self.subscriptions = []
        self.events = []

    def subscribe(self, topic, callback):
        self.subscriptions.append((topic, callback))

    def publish(self, topic, payload=None, source=None):
        event = {"topic": topic, "payload": payload or {}, "source": source}
        self.events.append(event)
        return event


class SimpleTransport:
    def __init__(self, name):
        self.name = name
        self.running = False

    def start(self):
        self.running = True
        return self

    def stop(self):
        self.running = False
        return self

    def health(self):
        return {"running": self.running}

    def register_agent(self, *args, **kwargs):
        return None


class FakeConfig:
    def load(self):
        return SimpleNamespace(tick_seconds=0.01)


class FakeLogger:
    def log(self, *args, **kwargs):
        return None


class FakeState:
    def __init__(self):
        self.current = "INITIALIZING"

    def transition(self, state):
        self.current = state


class FakeMetrics:
    def increment(self, *args, **kwargs):
        return None


class FakeScheduler:
    def run_pending(self):
        return None


class FakeHealthMonitor:
    def check(self):
        return {"healthy": True}


class FakeLifecycle:
    def __init__(self, bus=None):
        self.bus = bus
        self.startup_calls = []
        self.shutdown_calls = []

    def startup(self, *args, **kwargs):
        self.startup_calls.append((args, kwargs))
        return None

    def shutdown(self, *args, **kwargs):
        self.shutdown_calls.append((args, kwargs))
        return None


class FakeGovernor:
    def __init__(self, bus, state):
        self.bus = bus
        self.state = state


class FakeKnowledgeGraph:
    def __init__(self, bus=None, root=None):
        self.bus = bus
        self.root = root

    def collect_health(self):
        return SimpleNamespace(to_dict=lambda: {"running": True, "node_count": 0, "edge_count": 0})


class FakeGoalManager:
    def __init__(self, *args, **kwargs):
        pass

    def create_goal(self, *args, **kwargs):
        return None


class FakeRecoveryManager:
    def __init__(self, *args, **kwargs):
        pass

    def scan_and_recover(self):
        return 0


class FakePluginLoader:
    def __init__(self):
        self.load_calls = 0

    def load(self):
        self.load_calls += 1


class FakeGrokProvider:
    def __init__(self, bus):
        self.bus = bus

    def initialize(self):
        return True

    def health(self):
        return {"provider_ready": True}


class FakeGrokAgent:
    def execute(self, *args, **kwargs):
        return None


def test_runtime_bootstrap_smoke(monkeypatch, tmp_path):
    monkeypatch.setattr(bootstrap_mod, "Config", FakeConfig)
    monkeypatch.setattr(bootstrap_mod, "Logger", FakeLogger)
    monkeypatch.setattr(bootstrap_mod, "RuntimeState", FakeState)
    monkeypatch.setattr(bootstrap_mod, "Metrics", FakeMetrics)
    monkeypatch.setattr(bootstrap_mod, "Scheduler", FakeScheduler)
    monkeypatch.setattr(bootstrap_mod, "HealthMonitor", FakeHealthMonitor)
    monkeypatch.setattr(bootstrap_mod, "Lifecycle", FakeLifecycle)
    monkeypatch.setattr(bootstrap_mod, "Governor", FakeGovernor)
    monkeypatch.setattr(bootstrap_mod, "AccessibilityDriver", lambda bus: SimpleTransport("accessibility"))
    monkeypatch.setattr(bootstrap_mod, "ClipboardEventBridge", lambda bus: SimpleTransport("clipboard"))
    monkeypatch.setattr(bootstrap_mod, "AdaptivePlanner", lambda bus, queue, root=None: SimpleTransport("adaptive_planner"))
    monkeypatch.setattr(bootstrap_mod, "WorkflowExecutor", lambda bus, queue: SimpleTransport("workflow_executor"))
    monkeypatch.setattr(bootstrap_mod, "GrokProvider", FakeGrokProvider)
    monkeypatch.setattr(bootstrap_mod, "KnowledgeGraph", FakeKnowledgeGraph)
    monkeypatch.setattr(bootstrap_mod, "AgentCoordinator", lambda bus, queue: SimpleTransport("agent_coordinator"))
    monkeypatch.setattr(bootstrap_mod, "GoalManager", FakeGoalManager)
    monkeypatch.setattr(bootstrap_mod, "RecoveryManager", FakeRecoveryManager)
    monkeypatch.setattr(bootstrap_mod, "PluginLoader", FakePluginLoader)
    monkeypatch.setattr(bootstrap_mod, "GrokAgent", FakeGrokAgent)

    runtime = bootstrap_mod.build_runtime_stack(bus=FakeBus(), root=tmp_path)
    registry = runtime["transport_registry"]

    registry.start_all()
    health = registry.health()
    reports = registry.publish_health()

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
    assert all(report["running"] is True for report in health.values())
    assert len(reports) == len(expected)

    registry.stop_all()
    stopped = registry.health()
    assert all(report["running"] is False for report in stopped.values())
