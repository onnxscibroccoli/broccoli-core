#!/data/data/com.termux/files/usr/bin/bash
echo "=== Broccoli Core Runtime Starting ==="

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

    governor = Governor(bus, state)
    accessibility = AccessibilityDriver(bus)
    plugins = PluginLoader(bus)
    plugins.load()

    lifecycle.startup([config, logger, bus, state, metrics, scheduler, health, governor, accessibility, plugins])

    state.transition("RUNNING")
    logger.log("INFO", "Core Runtime with Governor + Semantic Accessibility + Plugins started")

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

echo "✅ Starting runtime..."
python3 main.py
