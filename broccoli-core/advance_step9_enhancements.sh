#!/data/data/com.termux/files/usr/bin/bash
cd /data/data/com.termux/files/home/broccoli-core

echo "=== Phase 3 Step 9: Enhanced Governor (Better Tasks + Logging) ==="

# Improve engine with more robust task handling
cat > governor/engine.py <<'EOF'
import time
from runtime.services.daemon import Daemon
from runtime.logger import setup_logger
from drivers.accessibility.driver import AccessibilityDriver
from workflow.queue import TaskQueue
from workflow.executor import WorkflowExecutor
from runtime.plugin_loader import load_plugins
from workflow.task import Task

# Shizuku
try:
    from drivers.shizuku.rish import RishDriver
    SHIZUKU_AVAILABLE = True
except ImportError:
    SHIZUKU_AVAILABLE = False

class Governor:
    def __init__(self):
        self.logger = setup_logger("governor")
        self.accessibility = AccessibilityDriver()
        self.queue = TaskQueue()
        self.executor = WorkflowExecutor()
        self.plugins = load_plugins()
        self.running = True
        self.health_score = 100
        self.cycle_count = 0
        
        self.rish = RishDriver() if SHIZUKU_AVAILABLE else None
        if self.rish and self.rish.available:
            self.logger.info("✅ Shizuku/rish driver initialized")

    def environment_awareness(self):
        if self.rish and self.rish.available:
            info = self.rish.system_info()
            self.logger.info(f"System via rish: {info.get('output', 'N/A')}")
            return info
        return None

    def observe(self):
        snapshot = self.accessibility.snapshot()
        node_count = len(snapshot.get('nodes', []))
        self.logger.info(f"Observed screen - nodes: {node_count}")
        return snapshot

    def health_check(self):
        healthy = self.accessibility.available() and len(self.plugins) > 0
        self.health_score = 100 if healthy else max(0, self.health_score - 20)
        self.logger.info(f"Health: {self.health_score}% | Cycle: {self.cycle_count}")
        return self.health_score > 60

    def generate_task(self):
        """More intelligent task generation"""
        self.cycle_count += 1
        if self.cycle_count % 5 == 0:
            return Task(goal="Analyze screen for UI changes", priority="HIGH")
        return Task(goal="Process user screen interaction", priority="NORMAL")

    def run_cycle(self):
        if not self.health_check():
            self.logger.warning("System degraded - recovery needed")
            return

        self.observe()
        self.environment_awareness()

        task = self.generate_task()
        self.queue.enqueue(task)

        result = self.executor.execute(task)
        self.queue.complete(task, result)

        self.logger.info(f"Governor cycle {self.cycle_count} completed")

    def start(self):
        self.logger.info("Governor Engine started")
        while self.running:
            self.run_cycle()
            time.sleep(3)

    def stop(self):
        self.running = False
        self.logger.info("Governor stopped")
EOF

chmod +x run.sh
echo "✅ Step 9: Enhanced Governor Ready"
echo "Run: ./run.sh"
