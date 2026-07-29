from types import SimpleNamespace

from runtime import bootstrap as bootstrap_mod
from runtime.transports.events import TRANSPORT_RECOVERY_FAILED


class FakeBus:
    def __init__(self):
        self.subscriptions = []
        self.events = []

    def subscribe(self, topic, callback):
        self.subscriptions.append((topic, callback))

    def publish(self, topic, payload=None, source=None):
        event = SimpleNamespace(topic=topic, payload=payload or {}, source=source)
        self.events.append(event)
        return event


class PassingTransport:
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

    def register_agent(self, *args, **kwargs):
        return None


class FailingStartTransport(PassingTransport):
    def start(self):
        self.start_calls += 1
        raise RuntimeError(f"{self.name} failed to start")


class FailingStopTransport(PassingTransport):
    def stop(self):
        self.stop_calls += 1
        raise RuntimeError(f"{self.name} failed to stop")


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
    def startup(self, *args, **kwargs):
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
    def __init__(self, transport=None):
        self.transport = transport

    def load(self):
        return None


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


def _patch_bootstrap(monkeypatch, plugin_loader=None):
    monkeypatch.setattr(bootstrap_mod, "Config", FakeConfig)
    monkeypatch.setattr(bootstrap_mod, "Logger", FakeLogger)
    monkeypatch.setattr(bootstrap_mod, "RuntimeState", FakeState)
    monkeypatch.setattr(bootstrap_mod, "Metrics", FakeMetrics)
    monkeypatch.setattr(bootstrap_mod, "Scheduler", FakeScheduler)
    monkeypatch.setattr(bootstrap_mod, "HealthMonitor", FakeHealthMonitor)
    monkeypatch.setattr(bootstrap_mod, "Lifecycle", FakeLifecycle)
    monkeypatch.setattr(bootstrap_mod, "Governor", FakeGovernor)
    monkeypatch.setattr(bootstrap_mod, "AccessibilityDriver", lambda bus: PassingTransport("accessibility"))
    monkeypatch.setattr(bootstrap_mod, "ClipboardEventBridge", lambda bus: PassingTransport("clipboard"))
    monkeypatch.setattr(bootstrap_mod, "AdaptivePlanner", lambda bus, queue, root=None: PassingTransport("adaptive_planner"))
    monkeypatch.setattr(bootstrap_mod, "WorkflowExecutor", lambda bus, queue: PassingTransport("workflow_executor"))
    monkeypatch.setattr(bootstrap_mod, "GrokProvider", FakeGrokProvider)
    monkeypatch.setattr(bootstrap_mod, "KnowledgeGraph", FakeKnowledgeGraph)
    monkeypatch.setattr(bootstrap_mod, "AgentCoordinator", lambda bus, queue: PassingTransport("agent_coordinator"))
    monkeypatch.setattr(bootstrap_mod, "GoalManager", FakeGoalManager)
    monkeypatch.setattr(bootstrap_mod, "RecoveryManager", FakeRecoveryManager)
    monkeypatch.setattr(bootstrap_mod, "PluginLoader", lambda: plugin_loader or FakePluginLoader())
    monkeypatch.setattr(bootstrap_mod, "GrokAgent", FakeGrokAgent)


def test_bootstrap_registry_reports_start_failure(monkeypatch, tmp_path):
    failing_plugin_transport = FailingStartTransport("plugin_loader")
    plugin_loader = FakePluginLoader(transport=failing_plugin_transport)
    _patch_bootstrap(monkeypatch, plugin_loader=plugin_loader)

    runtime = bootstrap_mod.build_runtime_stack(bus=FakeBus(), root=tmp_path)
    registry = runtime["transport_registry"]
    registry.register("plugin_loader", failing_plugin_transport)

    registry.start_all()

    failures = [event for event in runtime["bus"].events if event.topic == TRANSPORT_RECOVERY_FAILED]
    assert len(failures) == 1
    assert failures[0].payload["transport"] == "plugin_loader"
    assert failures[0].payload["phase"] == "start_all"
    assert "failed to start" in failures[0].payload["error"]


def test_bootstrap_registry_reports_stop_failure(monkeypatch, tmp_path):
    failing_plugin_transport = FailingStopTransport("plugin_loader")
    plugin_loader = FakePluginLoader(transport=failing_plugin_transport)
    _patch_bootstrap(monkeypatch, plugin_loader=plugin_loader)

    runtime = bootstrap_mod.build_runtime_stack(bus=FakeBus(), root=tmp_path)
    registry = runtime["transport_registry"]
    registry.register("plugin_loader", failing_plugin_transport)

    registry.start_all()
    registry.stop_all()

    failures = [event for event in runtime["bus"].events if event.topic == TRANSPORT_RECOVERY_FAILED]
    assert len(failures) == 1
    assert failures[0].payload["transport"] == "plugin_loader"
    assert failures[0].payload["phase"] == "stop_all"
    assert "failed to stop" in failures[0].payload["error"]
