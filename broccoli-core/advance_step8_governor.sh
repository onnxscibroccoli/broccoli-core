#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

echo "=== Phase 3 Step 8: Full Governor Engine + Health Monitor ==="

cat > governor/engine.py <<'PY'
import time
from runtime.services.daemon import Daemon
from runtime.logger import setup_logger
from drivers.accessibility.driver import AccessibilityDriver
from workflow.queue import TaskQueue
from workflow.executor import WorkflowExecutor
from runtime.plugin_loader import load_plugins

class Governor:
    def __init__(self):
        self.logger = setup_logger("governor")
        self.accessibility = AccessibilityDriver()
        self.queue = TaskQueue()
        self.executor = WorkflowExecutor()
        self.plugins = load_plugins()
        self.running = True
        self.health_score = 100

    def observe(self):
        snapshot = self.accessibility.snapshot()
        self.logger.info(f"Observed screen - nodes: {len(snapshot.get('nodes', []))}")
        return snapshot

    def health_check(self):
        healthy = self.accessibility.available() and len(self.plugins) > 0
        self.health_score = 100 if healthy else max(0, self.health_score - 20)
        self.logger.info(f"Health: {self.health_score}%")
        return self.health_score > 60

    def run_cycle(self):
        if not self.health_check():
            self.logger.warning("System degraded - recovery needed")
            return

        self.observe()

        # Example task generation
        task = Task(goal="Process user screen interaction", priority="NORMAL")
        self.queue.enqueue(task)

        result = self.executor.execute(task)
        self.queue.complete(task, result)

        self.logger.info("Governor cycle completed")

    def start(self):
        self.logger.info("Governor Engine started")
        while self.running:
            self.run_cycle()
            time.sleep(3)  # Governor tick

    def stop(self):
        self.running = False
        self.logger.info("Governor stopped")
PY

# Update main to use full Governor
cat > runtime/main.py <<'PY'
import sys
sys.path.insert(0, '.')

from governor.engine import Governor

def main():
    print("🚀 Broccoli Core - Phase 3: Full Governor Engine\n")
    
    governor = Governor()
    try:
        governor.start()
    except KeyboardInterrupt:
        governor.stop()
        print("\n✅ Governor shutdown complete.")

if __name__ == "__main__":
    main()
PY

cat > run.sh <<'RUN'
#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core
PYTHONPATH=. python3 runtime/main.py
RUN

chmod +x run.sh advance_step8_governor.sh
echo "✅ Step 8 Complete - Full Governor Engine"
echo "Run: ./run.sh"
