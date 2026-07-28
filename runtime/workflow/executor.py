from workflow.queue import TaskQueue
from workflow.task import Task
from event_bus import EventBus

class Executor:
    def __init__(self, bus: EventBus, queue: TaskQueue):
        self.bus = bus
        self.queue = queue
        self.bus.subscribe("PlannerTaskCreated", self.execute_next)

    def execute_next(self, task: Task):
        print(f"Executor: Running {task.id}")
        try:
            # Example: tap send if action is send
            if task.action == "tap_send":
                from drivers.accessibility.driver import AccessibilityDriver
                driver = AccessibilityDriver(self.bus)  # temporary
                driver.tap(984, 1381)
            task.status = "completed"
            self.bus.publish("TaskCompleted", task)
        except Exception as e:
            task.status = "failed"
            self.bus.publish("TaskFailed", {"task": task, "error": str(e)})

    def run_pending(self):
        task = self.queue.dequeue()
        if task:
            self.execute_next(task)
