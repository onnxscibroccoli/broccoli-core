from runtime.eventbus import EventBus
from runtime.workflow.queue import TaskQueue

class AgentCoordinator:
    def __init__(self, bus: EventBus, queue: TaskQueue):
        self.bus = bus
        self.queue = queue
        self.agents = {}
        self.bus.subscribe("TaskCompleted", self.coordinate_next)

    def register_agent(self, name, agent):
        self.agents[name] = agent
        print(f"Coordinator: Registered agent {name}")

    def coordinate_next(self, task):
        print(f"Coordinator: Task {task.id} completed → coordinating next agents")
        # Example: trigger Grok for research after send
        self.bus.publish("AgentCoordination", {"task": task})

    def dispatch(self, agent_name, task):
        if agent_name in self.agents:
            self.agents[agent_name].execute(task)
