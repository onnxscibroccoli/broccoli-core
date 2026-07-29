from runtime.eventbus.service import bus
from runtime.governor.repo_governor import RepoGovernor

from runtime.drivers.accessibility.consumers import register_accessibility_consumers
from runtime.clipboard.adapter import ClipboardEventBridge
from runtime.clipboard.consumers import register_clipboard_consumers
from runtime.clipboard.supervisor import register_clipboard_supervisor
from runtime.config import Config
from runtime.logger import Logger
from runtime.state import RuntimeState
from runtime.metrics import Metrics
from runtime.scheduler import Scheduler
from runtime.health import HealthMonitor
from runtime.lifecycle import Lifecycle
from runtime.governor.engine import Governor
from runtime.drivers.accessibility.driver import AccessibilityDriver
from runtime.plugin_loader import PluginLoader
from runtime.planner.adaptive import AdaptivePlanner
from runtime.workflow.queue import TaskQueue
from runtime.workflow.executor import Executor as WorkflowExecutor
from runtime.providers.grok import GrokProvider
from runtime.memory.knowledge_graph import KnowledgeGraph
from runtime.agents.coordinator import AgentCoordinator
from runtime.agents.grok_agent import GrokAgent
from runtime.autonomy.goal_manager import GoalManager
from runtime.autonomy.recovery import RecoveryManager
import time

# How often (in ticks) to run a full recovery scan.
# Event-driven recovery still happens immediately on GOAL_FAILED.
RECOVERY_SCAN_EVERY = 10


def main():
    config = Config().load()
    logger = Logger()
    state = RuntimeState()
    metrics = Metrics()
    scheduler = Scheduler()
    health = HealthMonitor()
    lifecycle = Lifecycle()

    queue = TaskQueue()
    governor = Governor(bus, state)
    accessibility = AccessibilityDriver(bus)
    planner = AdaptivePlanner(bus, queue)
    workflow_executor = WorkflowExecutor(bus, queue)
    grok = GrokProvider(bus)
    kg = KnowledgeGraph()
    coordinator = AgentCoordinator(bus, queue)
    grok_agent = GrokAgent()
    coordinator.register_agent("grok", grok_agent)

    # Shared GoalManager + RecoveryManager (same in-memory Executor)
    goal_manager = GoalManager(bus, queue, kg)
    recovery = RecoveryManager(bus)

    plugins = PluginLoader()
    plugins.load()

    register_accessibility_consumers(bus, metrics)
    register_clipboard_consumers(bus, metrics)
    clipboard_bridge = ClipboardEventBridge(bus)
    register_clipboard_supervisor(bus, clipboard_bridge, metrics)
    clipboard_bridge.start()

    lifecycle.startup([
        config, logger, bus, state, metrics, scheduler, health,
        governor, accessibility, planner, workflow_executor,
        grok, kg, coordinator, goal_manager, recovery, plugins,
        clipboard_bridge,
    ])

    grok.initialize()

    # Example goal (kept for smoke visibility)
    goal_manager.create_goal("test_goal", "Test autonomous task")

    state.transition("RUNNING")
    logger.log("INFO", "Autonomous Task Executive started", "Core")

    tick = 0
    try:
        while True:
            bus.publish("TICK")
            scheduler.run_pending()
            workflow_executor.run_pending()
            health_report = health.check()
            bus.publish("HEALTH_CHECK", health_report, source="HealthMonitor")
            bus.publish(
                "CLIPBOARD_BRIDGE_HEALTH",
                clipboard_bridge.health(),
                source="ClipboardEventBridge",
            )
            health.check()
            metrics.increment("loop_cycles")

            tick += 1
            if tick % RECOVERY_SCAN_EVERY == 0:
                recovered = recovery.scan_and_recover()
                if recovered:
                    logger.log("INFO", f"Recovered {recovered} goal(s)", "Recovery")

            time.sleep(config.tick_seconds)
    except KeyboardInterrupt:
        logger.log("INFO", "Shutdown requested", "Core")
        state.transition("STOPPED")
    finally:
        clipboard_bridge.stop()


if __name__ == "__main__":
    main()


# Capability monitoring hook
def capability_status(event):
    try:
        print(
            "Capability:",
            event.get("capability"),
            "available=",
            event.get("available"),
            "fallback=",
            event.get("fallback")
        )
    except Exception:
        pass


try:
    bus.subscribe(
        "CAPABILITY_STATUS",
        capability_status
    )
except Exception:
    pass
