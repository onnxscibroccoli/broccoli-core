from runtime.eventbus.service import bus
from runtime.governor.repo_governor import RepoGovernor

from runtime.drivers.accessibility.consumers import register_accessibility_consumers
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
from workflow.executor import Executor as WorkflowExecutor
from providers.grok import GrokProvider
from memory.knowledge_graph import KnowledgeGraph
from agents.coordinator import AgentCoordinator
from agents.grok_agent import GrokAgent
from autonomy.goal_manager import GoalManager
from autonomy.recovery import RecoveryManager
import time

# How often (in ticks) to run a full recovery scan.
# Event-driven recovery still happens immediately on GOAL_FAILED.
RECOVERY_SCAN_EVERY = 10

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

    lifecycle.startup([
        config, logger, bus, state, metrics, scheduler, health,
        governor, accessibility, planner, workflow_executor,
        grok, kg, coordinator, goal_manager, recovery, plugins
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

if __name__ == "__main__":
    main()
