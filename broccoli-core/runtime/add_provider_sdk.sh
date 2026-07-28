#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Provider SDK (Grok + Agnostic) ==="

# providers/base.py
mkdir -p providers
cat > providers/base.py << 'BASE'
from abc import ABC, abstractmethod
class Provider(ABC):
    @abstractmethod
    def initialize(self):
        pass
    @abstractmethod
    def send(self, message):
        pass
    @abstractmethod
    def health(self):
        pass
    @abstractmethod
    def shutdown(self):
        pass
BASE

# providers/grok.py
cat > providers/grok.py << 'GROK'
from base import Provider
from event_bus import EventBus

class GrokProvider(Provider):
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.initialized = False

    def initialize(self):
        self.initialized = True
        print("GrokProvider initialized")
        self.bus.publish("ProviderConnected", "grok")

    def send(self, message):
        print(f"GrokProvider: Sending '{message[:50]}...'")
        self.bus.publish("ConversationUpdated", {"provider": "grok", "message": message})
        return True

    def health(self):
        return {"status": "healthy", "provider": "grok"}

    def shutdown(self):
        print("GrokProvider shutdown")
BASE

# Update main.py to include provider
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
    grok = GrokProvider(bus)
    plugins = PluginLoader()
    plugins.load()

    lifecycle.startup([config, logger, bus, state, metrics, scheduler, health, governor, accessibility, planner, grok, plugins])

    grok.initialize()

    state.transition("RUNNING")
    logger.log("INFO", "Core Runtime with Provider SDK started")

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

echo "✅ Provider SDK (Grok) integrated"
echo "Restarting runtime..."
pkill -f "python3 main.py" 2>/dev/null || true
python3 main.py
