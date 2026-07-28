"""GoalManager – façade over a shared Executor."""
from .executor import Executor, GoalStatus
from event_bus import EventBus

# module-level shared executor so GoalManager + RecoveryManager see the same goals
_shared_executor = None

def get_shared_executor(bus: EventBus = None) -> Executor:
    global _shared_executor
    if _shared_executor is None:
        _shared_executor = Executor(event_bus=bus)
    return _shared_executor

class GoalManager:
    def __init__(self, bus: EventBus, queue=None, kg=None):
        self.bus = bus
        self.ex = get_shared_executor(bus)
        self.queue = queue
        self.kg = kg

    def create_goal(self, name: str, description: str = ""):
        g = self.ex.create_goal(name, description)
        self.ex.start_goal(g.id)
        return g

    def list_goals(self, status=None):
        return self.ex.list_goals(status)

    def get_goal(self, goal_id: str):
        return self.ex.get_goal(goal_id)

    def complete(self, goal_id: str):
        self.ex.complete_goal(goal_id)

    def fail(self, goal_id: str, reason: str):
        self.ex.fail_goal(goal_id, reason)
