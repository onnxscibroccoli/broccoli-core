from __future__ import annotations

import time

from runtime.eventbus import EventBus
from runtime.workflow.queue import TaskQueue


class AgentCoordinator:
    def __init__(self, bus: EventBus, queue: TaskQueue):
        self.bus = bus
        self.queue = queue
        self.agents = {}
        self._running = False
        self.last_coordination_at = None
        self.bus.subscribe("TaskCompleted", self.coordinate_next)

    def start(self):
        self._running = True
        return self

    def stop(self):
        self._running = False
        return self

    def health(self):
        return {
            "running": self._running,
            "agent_count": len(self.agents),
            "queued_tasks": len(self.queue.queue),
            "last_coordination_at": self.last_coordination_at,
        }

    def register_agent(self, name, agent):
        self.agents[name] = agent
        print(f"Coordinator: Registered agent {name}")

    def coordinate_next(self, task):
        if not self._running:
            return

        print(f"Coordinator: Task {task.id} completed → coordinating next agents")
        self.last_coordination_at = time.time()
        self.bus.publish("AgentCoordination", {"task": task})

    def dispatch(self, agent_name, task):
        if not self._running:
            return

        if agent_name in self.agents:
            self.agents[agent_name].execute(task)
