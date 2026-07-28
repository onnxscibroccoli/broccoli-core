#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

echo "=== Step 5 Fixed ==="

mkdir -p runtime/services runtime/config workflow drivers/accessibility providers

cat > runtime/config/settings.py <<'PY'
from dataclasses import dataclass
@dataclass
class RuntimeConfig:
    tick_seconds: float = 2.0
PY

cat > runtime/logger.py <<'PY'
import logging
import sys
def setup_logger(name="broccoli"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    logger.addHandler(handler)
    return logger
PY

cat > runtime/metrics.py <<'PY'
class Metrics:
    def __init__(self):
        self.cycles = 0
    def increment(self, key):
        if key == "cycle": self.cycles += 1
PY

cat > runtime/services/daemon.py <<'PY'
import time
from runtime.logger import setup_logger
from runtime.metrics import Metrics

class Daemon:
    def __init__(self):
        self.logger = setup_logger("daemon")
        self.metrics = Metrics()
        self.running = False

    def start(self):
        self.running = True
        self.logger.info("Broccoli Daemon started")
        try:
            while self.running:
                self.metrics.increment("cycle")
                self.logger.info(f"Governor cycle {self.metrics.cycles}")
                time.sleep(2)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.running = False
        self.logger.info("Daemon stopped")
PY

cat > drivers/accessibility/driver.py <<'PY'
class AccessibilityDriver:
    def available(self): return True
    def snapshot(self): return {"nodes": []}
    def perform_action(self, action):
        print(f"  [Accessibility] {action}")
        return True
PY

cat > providers/grok.py <<'PY'
class GrokProvider:
    def initialize(self):
        print("[grok] initialized")
        return True
    def send(self, request):
        return {"content": f"Reply to: {request.get('message','')}"}
PY

cat > workflow/task.py <<'PY'
from dataclasses import dataclass
from typing import Dict, Optional
import uuid, time

@dataclass
class Task:
    goal: str
    task_id: str = ""
    priority: str = "NORMAL"
    status: str = "queued"
    result: Optional[Dict] = None

    def __post_init__(self):
        if not self.task_id:
            self.task_id = str(uuid.uuid4())[:8]
PY

cat > workflow/queue.py <<'PY'
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
PY

cat > workflow/executor.py <<'PY'
from workflow.task import Task
from providers.grok import GrokProvider

class WorkflowExecutor:
    def __init__(self):
        self.provider = GrokProvider()
        self.provider.initialize()

    def execute(self, task: Task) -> dict:
        print(f"⚙️ Executing: {task.goal}")
        try:
            resp = self.provider.send({"message": task.goal})
            return {"success": True, "content": resp.get("content", "")}
        except:
            return {"success": False, "error": "failed"}
PY

cat > runtime/main.py <<'PY'
import sys
sys.path.insert(0, '.')

from runtime.services.daemon import Daemon
from drivers.accessibility.driver import AccessibilityDriver
from workflow.task import Task
from workflow.queue import TaskQueue
from workflow.executor import WorkflowExecutor

def main():
    print("🚀 Broccoli Core - Step 5 Autonomous Workflow\n")
    
    acc = AccessibilityDriver()
    print("✅ Accessibility ready")

    queue = TaskQueue()
    executor = WorkflowExecutor()

    tasks = [
        Task(goal="Summarize current screen content", priority="HIGH"),
        Task(goal="Send friendly message via accessibility", priority="NORMAL"),
        Task(goal="Check system health", priority="LOW")
    ]

    for t in tasks:
        queue.enqueue(t)

    while True:
        task = queue.dequeue()
        if not task: break
        result = executor.execute(task)
        queue.complete(task, result)

    print(f"\n🎯 Workflow completed — {len(queue.completed)} tasks done.")

    daemon = Daemon()
    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.stop()
        print("\n✅ Shutdown complete.")

if __name__ == "__main__":
    main()
PY

cat > run.sh <<'RUN'
#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core
PYTHONPATH=. python3 runtime/main.py
RUN

chmod +x run.sh
echo "✅ Step 5 Fully Fixed"
echo "Run: ./run.sh"
