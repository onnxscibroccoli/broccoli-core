#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Adaptive Planning Engine ==="

# planner/adaptive.py
cat > planner/adaptive.py << 'ADAPTIVE'
from planner.planner import Planner
from event_bus import EventBus
from workflow.queue import TaskQueue

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
ADAPTIVE

# Update main.py to use AdaptivePlanner
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
from planner.adaptive import AdaptivePlanner
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
    planner = AdaptivePlanner(bus, queue)
    executor = Executor(bus, queue)
    grok = GrokProvider(bus)
    plugins = PluginLoader()
    plugins.load()

    lifecycle.startup([config, logger, bus, state, metrics, scheduler, health, governor, accessibility, planner, executor, grok, plugins])

    grok.initialize()

    state.transition("RUNNING")
    logger.log("INFO", "Adaptive Planning Engine started", "Core")

    try:
        while True:
            bus.publish("TICK")
            scheduler.run_pending()
            executor.run_pending()
            health.check()
            metrics.increment("loop_cycles")
            time.sleep(config.tick_seconds)
    except KeyboardInterrupt:
        logger.log("INFO", "Shutdown requested", "Core")
        state.transition("STOPPED")

if __name__ == "__main__":
    main()
MAIN

echo "✅ Adaptive Planning Engine integrated"
echo "Restarting runtime..."
pkill -f "python3 main.py" 2>/dev/null || true
python3 main.py
