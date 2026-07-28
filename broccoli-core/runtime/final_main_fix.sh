#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Final Main Fix ==="

# PluginLoader
cat > plugin_loader.py << 'PLUG'
class PluginLoader:
    def load(self):
        print("Plugins loaded: 1 (example)")
PLUG

# Clean main.py
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
from memory.knowledge_graph import KnowledgeGraph
from agents.coordinator import AgentCoordinator
from agents.grok_agent import GrokAgent
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
    kg = KnowledgeGraph()
    coordinator = AgentCoordinator(bus, queue)
    grok_agent = GrokAgent()
    coordinator.register_agent("grok", grok_agent)
    plugins = PluginLoader()
    plugins.load()

    lifecycle.startup([config, logger, bus, state, metrics, scheduler, health, governor, accessibility, planner, executor, grok, kg, coordinator, plugins])

    grok.initialize()

    state.transition("RUNNING")
    logger.log("INFO", "Full Production Runtime started", "Core")

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
