from runtime.workflow.queue import TaskQueue
from runtime.workflow.task import Task
from runtime.eventbus import EventBus


class Executor:
    def __init__(self, bus: EventBus, queue: TaskQueue):
        self.bus = bus
        self.queue = queue
        self._running = False

        self.bus.subscribe(
            "PlannerTaskCreated",
            self.execute_next,
        )

    def start(self):
        self._running = True
        return self

    def stop(self):
        self._running = False
        return self

    def health(self):
        return {
            "running": self._running,
            "queued_tasks": len(self.queue.queue),
        }

    def execute_next(self, task: Task):
        if not self._running:
            return

        print(f"Executor: Running {task.id}")

        try:
            if task.action == "tap_send":
                self.bus.publish(
                    "ACCESSIBILITY_TAP",
                    {
                        "x": 984,
                        "y": 1381,
                    },
                    source="WorkflowExecutor",
                )

            task.status = "completed"

            self.bus.publish(
                "TaskCompleted",
                task,
            )

        except Exception as exc:
            task.status = "failed"

            self.bus.publish(
                "TaskFailed",
                {
                    "task": task,
                    "error": str(exc),
                },
            )

    def run_pending(self):
        if not self._running:
            return

        task = self.queue.dequeue()

        if task:
            self.execute_next(task)
