from pathlib import Path

from runtime.agents.coordinator import AgentCoordinator
from runtime.memory.knowledge_graph import KnowledgeGraph
from runtime.planner.adaptive import AdaptivePlanner
from runtime.plugin_loader import PluginLoader
from runtime.transports import KnowledgeGraphTransport, PluginLoaderTransport, ProviderTransport, TransportRegistry
from runtime.workflow.executor import Executor as WorkflowExecutor
from runtime.workflow.queue import TaskQueue


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


class FakeProvider:
    def __init__(self):
        self.initialized = 0

    def initialize(self):
        self.initialized += 1

    def health(self):
        return {"provider_ready": True}


class FakePluginLoader:
    def __init__(self):
        self.load_calls = 0

    def load(self):
        self.load_calls += 1


def test_transport_registry_smoke(tmp_path):
    bus = FakeBus()
    registry = TransportRegistry(bus)

    knowledge_graph = KnowledgeGraph(bus=bus, root=tmp_path)
    adaptive_planner = AdaptivePlanner(bus=bus, root=tmp_path, knowledge_graph=knowledge_graph)
    workflow_executor = WorkflowExecutor(bus, TaskQueue())
    agent_coordinator = AgentCoordinator(bus, TaskQueue())
    plugin_loader = PluginLoaderTransport(FakePluginLoader())
    grok_provider = ProviderTransport("grok", FakeProvider())

    registry.register("accessibility", SimpleTransport("accessibility"))
    registry.register("clipboard", SimpleTransport("clipboard"))
    registry.register("grok", grok_provider)
    registry.register("workflow_executor", workflow_executor)
    registry.register("adaptive_planner", adaptive_planner)
    registry.register("knowledge_graph", KnowledgeGraphTransport(knowledge_graph))
    registry.register("agent_coordinator", agent_coordinator)
    registry.register("plugin_loader", plugin_loader)

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
