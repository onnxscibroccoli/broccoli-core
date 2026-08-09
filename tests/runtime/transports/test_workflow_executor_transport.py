from runtime.workflow.executor import Executor
from runtime.workflow.queue import TaskQueue


class FakeBus:
    def __init__(self):
        self.events = []

    def subscribe(self, *args, **kwargs):
        pass

    def publish(self, topic, payload=None, source=None):
        self.events.append((topic, payload, source))


def test_executor_transport_lifecycle():
    bus = FakeBus()
    queue = TaskQueue()

    executor = Executor(bus, queue)

    assert executor.health()["running"] is False

    executor.start()

    assert executor.health()["running"] is True

    executor.stop()

    assert executor.health()["running"] is False
