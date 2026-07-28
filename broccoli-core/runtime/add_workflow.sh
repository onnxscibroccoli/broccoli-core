#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Autonomous Workflow Engine ==="

# workflow/executor.py
cat > workflow/executor.py << 'EXEC'
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
EXEC

# Update main.py to include executor
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
from workflow.executor import Executor
from providers.grok import GrokProvider
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
    executor = Executor(bus, queue)
    grok = GrokProvider(bus)
    plugins = PluginLoader()
    plugins.load()

    lifecycle.startup([config, logger, bus, state, metrics, scheduler, health, governor, accessibility, planner, executor, grok, plugins])

    grok.initialize()

    state.transition("RUNNING")
    logger.log("INFO", "Core Runtime with Autonomous Workflow Engine started")

    try:
        while True:
            bus.publish("TICK")
            scheduler.run_pending()
            executor.run_pending()
            health.check()
            metrics.increment("loop_cycles")
            time.sleep(config.tick_seconds)
    except KeyboardInterrupt:
        logger.log("INFO", "Shutdown requested")
        state.transition("STOPPED")

if __name__ == "__main__":
    main()
MAIN

echo "✅ Workflow Engine integrated"
echo "Restarting runtime..."
pkill -f "python3 main.py" 2>/dev/null || true
python3 main.py
