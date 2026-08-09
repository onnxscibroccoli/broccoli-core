from types import SimpleNamespace

from runtime.agents.coordinator import AgentCoordinator
from runtime.workflow.queue import TaskQueue


class FakeBus:
    def __init__(self):
        self.subscriptions = []
        self.events = []

    def subscribe(self, topic, callback):
        self.subscriptions.append((topic, callback))

    def publish(self, topic, payload=None, source=None):
        self.events.append((topic, payload, source))
        return {"topic": topic, "payload": payload or {}, "source": source}


def test_agent_coordinator_transport_lifecycle():
    bus = FakeBus()
    queue = TaskQueue()
    coordinator = AgentCoordinator(bus, queue)

    assert any(topic == "TaskCompleted" for topic, _ in bus.subscriptions)
    assert coordinator.health()["running"] is False

    coordinator.coordinate_next(SimpleNamespace(id="task-1"))
    assert not any(topic == "AgentCoordination" for topic, _, _ in bus.events)

    coordinator.start()
    coordinator.coordinate_next(SimpleNamespace(id="task-2"))

    assert any(topic == "AgentCoordination" for topic, _, _ in bus.events)
    assert coordinator.health()["running"] is True

    coordinator.stop()
    assert coordinator.health()["running"] is False
