from collections import deque
class TaskQueue:
    def __init__(self):
        self.queue = deque()
    def enqueue(self, task):
        self.queue.append(task)
        print(f"Queue: Enqueued {task.id}")
    def dequeue(self):
        if self.queue:
            return self.queue.popleft()
        return None
