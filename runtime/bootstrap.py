from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from runtime.agents.coordinator import AgentCoordinator
from runtime.agents.grok_agent import GrokAgent
from runtime.autonomy.goal_manager import GoalManager
from runtime.autonomy.recovery import RecoveryManager
from runtime.clipboard.adapter import ClipboardEventBridge
from runtime.config import Config
from runtime.drivers.accessibility.consumers import register_accessibility_consumers
from runtime.drivers.accessibility.driver import AccessibilityDriver
from runtime.eventbus.service import bus as default_bus
from runtime.governor.engine import Governor
from runtime.health import HealthMonitor
from runtime.lifecycle import Lifecycle
from runtime.logger import Logger
from runtime.memory.knowledge_graph import KnowledgeGraph
from runtime.metrics import Metrics
from runtime.plugin_loader import PluginLoader
from runtime.planner.adaptive import AdaptivePlanner
from runtime.providers.grok import GrokProvider
from runtime.scheduler import Scheduler
from runtime.state import RuntimeState
from runtime.transports import (
    KnowledgeGraphTransport,
    PluginLoaderTransport,
    ProviderTransport,
    TransportRegistry,
    register_transport_supervisor,
)
from runtime.workflow.executor import Executor as WorkflowExecutor
from runtime.workflow.queue import TaskQueue


def build_runtime_stack(
    bus=default_bus,
    root: Optional[Path] = None,
) -> Dict[str, Any]:
    runtime_root = Path(root or Path.cwd())

    config = Config().load()
    logger = Logger()
    state = RuntimeState()
    metrics = Metrics()
    scheduler = Scheduler()
    health = HealthMonitor()
    lifecycle = Lifecycle(bus)

    queue = TaskQueue()
    governor = Governor(bus, state)
    accessibility = AccessibilityDriver(bus)
    workflow_executor = WorkflowExecutor(bus, queue)
    grok = GrokProvider(bus)
    knowledge_graph = KnowledgeGraph(bus=bus, root=runtime_root)
    knowledge_graph_transport = KnowledgeGraphTransport(knowledge_graph)
    planner = AdaptivePlanner(
        bus=bus,
        root=runtime_root,
        knowledge_graph=knowledge_graph,
    )
    coordinator = AgentCoordinator(bus, queue)
    goal_manager = GoalManager(bus, queue, knowledge_graph)
    recovery = RecoveryManager(bus)

    grok_agent = GrokAgent(provider=grok, bus=bus)
    coordinator.register_agent("grok", grok_agent)

    plugins = PluginLoader()
    plugin_loader_transport = PluginLoaderTransport(plugins)

    transport_registry = TransportRegistry(bus)
    clipboard_bridge = ClipboardEventBridge(bus)
    grok_transport = ProviderTransport("grok", grok)

    transport_registry.register("accessibility", accessibility)
    transport_registry.register("clipboard", clipboard_bridge)
    transport_registry.register("grok", grok_transport)
    transport_registry.register("workflow_executor", workflow_executor)
    transport_registry.register("adaptive_planner", planner)
    transport_registry.register("knowledge_graph", knowledge_graph_transport)
    transport_registry.register("agent_coordinator", coordinator)
    transport_registry.register("plugin_loader", plugin_loader_transport)

    register_accessibility_consumers(bus, metrics)
    register_transport_supervisor(bus, transport_registry, metrics)

    return {
        "bus": bus,
        "config": config,
        "logger": logger,
        "state": state,
        "metrics": metrics,
        "scheduler": scheduler,
        "health": health,
        "lifecycle": lifecycle,
        "queue": queue,
        "governor": governor,
        "accessibility": accessibility,
        "planner": planner,
        "workflow_executor": workflow_executor,
        "grok": grok,
        "knowledge_graph": knowledge_graph,
        "knowledge_graph_transport": knowledge_graph_transport,
        "coordinator": coordinator,
        "goal_manager": goal_manager,
        "recovery": recovery,
        "plugins": plugins,
        "plugin_loader_transport": plugin_loader_transport,
        "transport_registry": transport_registry,
        "grok_agent": grok_agent,
    }
