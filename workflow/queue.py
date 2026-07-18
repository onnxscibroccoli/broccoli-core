from collections import deque
from workflow.task import Task
from typing import Optional

class TaskQueue:
    def __init__(self):
        self.queue = deque()
        self.completed = []

    def enqueue(self, task: Task):
        self.queue.append(task)
        print(f"📋 Enqueued: {task.goal} [{task.priority}]")

    def dequeue(self) -> Optional[Task]:
        return self.queue.popleft() if self.queue else None

    def complete(self, task: Task, result: dict):
        task.status = "completed"
        task.result = result
        self.completed.append(task)
        print(f"✅ Completed: {task.goal}")
