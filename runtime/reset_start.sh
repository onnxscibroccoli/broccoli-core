#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "=== Resetting & Starting Broccoli Core Runtime ==="

# config.py
cat > config.py << 'PY'
import json
from pathlib import Path
class Config:
    def __init__(self):
        self.tick_seconds = 2.0
        self.max_workers = 4
        self.log_level = "INFO"
    def load(self):
        return self
    def save(self):
        pass
PY

# logger.py
cat > logger.py << 'PY'
import datetime
class Logger:
    def log(self, level, msg):
        ts = datetime.datetime.now().isoformat()
        print(f"[{ts}] [{level}] {msg}")
PY

# event_bus.py
cat > event_bus.py << 'PY'
from collections import defaultdict
class EventBus:
    def __init__(self):
        self.handlers = defaultdict(list)
    def subscribe(self, event, handler):
        self.handlers[event].append(handler)
    def publish(self, event, payload=None):
        for handler in self.handlers[event]:
            handler(payload)
PY

# state.py
cat > state.py << 'PY'
STATE_INITIALIZING = "INITIALIZING"
STATE_RUNNING = "RUNNING"
STATE_RECOVERING = "RECOVERING"
STATE_STOPPING = "STOPPING"
STATE_STOPPED = "STOPPED"

class RuntimeState:
    def __init__(self):
        self.current = STATE_INITIALIZING
    def transition(self, new_state):
        print(f"State: {self.current} → {new_state}")
        self.current = new_state
PY

# metrics.py
cat > metrics.py << 'PY'
class Metrics:
    def __init__(self):
        self.counters = {}
    def increment(self, key):
        self.counters[key] = self.counters.get(key, 0) + 1
PY

# scheduler.py
cat > scheduler.py << 'PY'
class Scheduler:
    def run_pending(self):
        pass
PY

# health.py
cat > health.py << 'PY'
class HealthMonitor:
    def check(self):
        return {"status": "healthy"}
PY

# lifecycle.py
cat > lifecycle.py << 'PY'
class Lifecycle:
    def startup(self, components):
        print("Runtime starting...")
        for c in components:
            print(f"  ✓ {c.__class__.__name__}")
        print("Runtime READY")
PY

# governor/engine.py
mkdir -p governor
cat > governor/engine.py << 'GOV'
from state import RuntimeState
from event_bus import EventBus
class Governor:
    def __init__(self, bus: EventBus, state):
        self.bus = bus
        self.state = state
        self.bus.subscribe("TICK", self.on_tick)
    def on_tick(self, _):
        if self.state.current == "RUNNING":
            self.bus.publish("GOVERNOR_HEARTBEAT")
GOV

# drivers/accessibility/driver.py
mkdir -p drivers/accessibility
cat > drivers/accessibility/driver.py << 'ACC'
import subprocess
from event_bus import EventBus
class AccessibilityDriver:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.bus.subscribe("TICK", self.capture)
    def capture(self, _):
        try:
            result = subprocess.run(["rish", "-c", "uiautomator dump /sdcard/broccoli_ui.xml && cat /sdcard/broccoli_ui.xml"], capture_output=True, text=True, timeout=8)
            if result.stdout:
                self.bus.publish("AccessibilityCaptureReady", {"ok": True})
        except Exception:
            pass
ACC

# plugin_loader.py
cat > plugin_loader.py << 'PLUG'
class PluginLoader:
    def load(self):
        print("Plugins loaded: 1")
PLUG

# main.py
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
    plugins = PluginLoader()
    plugins.load()

    lifecycle.startup([config, logger, bus, state, metrics, scheduler, health, governor, accessibility, plugins])

    state.transition("RUNNING")
    logger.log("INFO", "Core Runtime started")

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

echo "✅ Runtime ready"
python3 main.py
