from runtime.planner.planner import Planner
from runtime.eventbus import EventBus
from runtime.workflow.queue import TaskQueue

class AdaptivePlanner(Planner):
    def __init__(self, bus: EventBus, queue: TaskQueue):
        super().__init__(bus, queue)
        self.learning_rate = 0.1
        self.success_history = []

    def plan_from_ui(self, payload):
        if payload and payload.get("primary_action"):
            task = self._adaptive_task("send_message", payload)
            self.queue.enqueue(task)
            self.bus.publish("PlannerTaskCreated", task)

    def _adaptive_task(self, goal, context):
        # Simple adaptation based on previous success
        priority = "HIGH" if len(self.success_history) > 5 else "NORMAL"
        return {"id": goal, "priority": priority, "context": context}

    def record_success(self, task_id):
        self.success_history.append(task_id)
        print(f"AdaptivePlanner: Learned success for {task_id}")
