"""RecoveryManager – uses the same shared Executor as GoalManager."""
from .executor import Executor, GoalStatus
from .goal_manager import get_shared_executor
from event_bus import EventBus

class RecoveryManager:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.ex = get_shared_executor(bus)
        if hasattr(bus, "subscribe"):
            try:
                bus.subscribe("GOAL_FAILED", self._on_failed)
            except Exception:
                pass

    def _on_failed(self, event):
        payload = event.get("payload", event) if isinstance(event, dict) else {}
        goal_id = payload.get("goal_id") if isinstance(payload, dict) else None
        if goal_id:
            self.ex.recover_goal(goal_id)

    def recover(self, goal_id: str) -> bool:
        return self.ex.recover_goal(goal_id)

    def scan_and_recover(self) -> int:
        count = 0
        for g in self.ex.list_goals(GoalStatus.FAILED):
            if self.ex.recover_goal(g.id):
                count += 1
        return count
