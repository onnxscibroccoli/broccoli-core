#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Adding Planner + Task Queue ==="

# planner/planner.py
mkdir -p planner
cat > planner/planner.py << 'PLAN'
from event_bus import EventBus
from workflow.task import Task
from workflow.queue import TaskQueue

class Planner:
    def __init__(self, bus: EventBus, queue: TaskQueue):
        self.bus = bus
        self.queue = queue
        self.bus.subscribe("AccessibilityCaptureReady", self.plan_from_ui)

    def plan_from_ui(self, payload):
        if payload and payload.get("primary_action"):
            task = Task(id="send_message", priority="HIGH", action="tap_send")
            self.queue.enqueue(task)
            self.bus.publish("PlannerTaskCreated", task)
        print("Planner: Task generated from UI")

    def generate_plan(self, goal):
        print(f"Planner: Generating plan for goal: {goal}")
        return [Task(id="goal", priority="NORMAL", action=goal)]
PLAN

# workflow/task.py
mkdir -p workflow
cat > workflow/task.py << 'TASK'
class Task:
    def __init__(self, id, priority="NORMAL", action=None):
        self.id = id
        self.priority = priority
        self.action = action
        self.status = "queued"
TASK

# workflow/queue.py
cat > workflow/queue.py << 'QUEUE'
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
QUEUE

# Update main.py to include planner
cat > main.py << 'MAIN'
from config import Config
from logger import Logger
from event_bus import EventBus
from state import RuntimeState
from metrics import Metrics
from scheduler import Scheduler
from health import HealthMonitor
from lifecycle import Lifecycle
from governor.engine import Governor
from drivers.accessibility.driver import AccessibilityDriver
from plugin_loader import PluginLoader
from planner.planner import Planner
from workflow.queue import TaskQueue
import time

def main():
    config = Config().load()
    logger = Logger()
    bus = EventBus()
    state = RuntimeState()
    metrics = Metrics()
    scheduler = Scheduler()
    health = HealthMonitor()
    lifecycle = Lifecycle()

    queue = TaskQueue()
    governor = Governor(bus, state)
    accessibility = AccessibilityDriver(bus)
    planner = Planner(bus, queue)
    plugins = PluginLoader()
    plugins.load()

    lifecycle.startup([config, logger, bus, state, metrics, scheduler, health, governor, accessibility, planner, plugins])

    state.transition("RUNNING")
    logger.log("INFO", "Core Runtime with Planner + Task Queue started")

    try:
        while True:
            bus.publish("TICK")
            scheduler.run_pending()
            health.check()
            metrics.increment("loop_cycles")
            time.sleep(config.tick_seconds)
    except KeyboardInterrupt:
        logger.log("INFO", "Shutdown requested")
        state.transition("STOPPED")

if __name__ == "__main__":
    main()
MAIN

echo "✅ Planner + Task Queue integrated"
echo "Restarting runtime..."
pkill -f "python3 main.py" 2>/dev/null || true
python3 main.py
