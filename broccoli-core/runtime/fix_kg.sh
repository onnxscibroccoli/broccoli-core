#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Fixing Knowledge Graph ==="

mkdir -p memory

cat > memory/knowledge_graph.py << 'KG'
from collections import defaultdict
import json
from pathlib import Path

class KnowledgeGraph:
    def __init__(self):
        self.graph = defaultdict(dict)
        self.memory_file = Path.home() / "broccoli-core/runtime/memory/knowledge.json"
        self.load()

    def add(self, subject, relation, object_, confidence=1.0):
        self.graph[subject][relation] = {"object": object_, "confidence": confidence}
        self.save()
        print(f"KG: {subject} {relation} {object_}")

    def query(self, subject, relation=None):
        if relation:
            return self.graph.get(subject, {}).get(relation)
        return self.graph.get(subject, {})

    def load(self):
        if self.memory_file.exists():
            try:
                self.graph = defaultdict(dict, json.loads(self.memory_file.read_text()))
            except Exception:
                pass

    def save(self):
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.memory_file.write_text(json.dumps(dict(self.graph), indent=2))
KG

# Update main.py
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
    plugins = PluginLoader()
    plugins.load()

    lifecycle.startup([config, logger, bus, state, metrics, scheduler, health, governor, accessibility, planner, executor, grok, kg, plugins])

    grok.initialize()

    state.transition("RUNNING")
    logger.log("INFO", "Knowledge Graph + Adaptive Planning started", "Core")

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

echo "✅ Knowledge Graph fixed"
echo "Starting runtime..."
python3 main.py
