import time
from runtime.logger import setup_logger
from drivers.accessibility.driver import AccessibilityDriver
from workflow.queue import TaskQueue
from workflow.executor import WorkflowExecutor
from runtime.plugin_loader import load_plugins
from workflow.task import Task
from workflow.decision import DecisionEngine
from drivers.overlay.virtual_display import VirtualSecondaryDisplay

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
        self.decision = DecisionEngine()
        self.overlay = VirtualSecondaryDisplay()
        self.running = True
        self.health_score = 100
        self.cycle_count = 0
        self.rish = RishDriver() if SHIZUKU_AVAILABLE else None
        if self.rish and self.rish.available:
            self.logger.info("✅ Shizuku/rish ready")

    def health_check(self):
        return True

    def run_cycle(self):
        self.cycle_count += 1
        snapshot = self.accessibility.snapshot()

        if self.overlay.is_idle():
            self.overlay.show_prompt("Codevelopment Mode Active - Awaiting input or task...")

        decision = self.decision.decide(snapshot, None)

        for p in self.plugins:
            p.on_cycle(self)
            p.on_decision(decision)

        task = Task(goal="Process user screen interaction", priority="NORMAL")
        self.queue.enqueue(task)
        result = self.executor.execute(task)
        self.queue.complete(task, result)

        self.logger.info(f"Governor cycle {self.cycle_count} completed")

    def start(self):
        self.logger.info("🧠 Intelligent Governor started")
        while self.running:
            self.run_cycle()
            time.sleep(3)

    def stop(self):
        self.running = False
        self.logger.info("Governor stopped")
