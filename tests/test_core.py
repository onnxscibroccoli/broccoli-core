import importlib
import unittest


def safe_import(module_name):
    """Import a current Broccoli Core module without hiding test failures."""
    try:
        return importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError):
        return None


class TestBroccoliCore(unittest.TestCase):
    """Core architectural smoke tests for the current runtime package."""

    def test_01_runtime_startup(self):
        main = safe_import("runtime.main")
        self.assertIsNotNone(main, "Runtime startup (runtime.main) failed to import.")

    def test_02_event_bus(self):
        event_bus = safe_import("runtime.event_bus")
        self.assertIsNotNone(event_bus, "Event Bus module missing.")

        if hasattr(event_bus, "EventBus"):
            bus = event_bus.EventBus()
            self.assertTrue(
                hasattr(bus, "publish") or hasattr(bus, "emit"),
                "EventBus missing publish/emit mechanism.",
            )

    def test_03_scheduler(self):
        scheduler = safe_import("runtime.scheduler")
        self.assertIsNotNone(scheduler, "Scheduler module missing.")

    def test_04_governor(self):
        engine = safe_import("runtime.governor.engine")
        self.assertIsNotNone(engine, "Governor engine module missing.")

    def test_05_accessibility_driver(self):
        driver = safe_import("runtime.drivers.accessibility.driver")
        self.assertIsNotNone(driver, "Accessibility Driver missing.")

    def test_06_semantic_parser(self):
        semantic = (
            safe_import("runtime.models.semantic")
            or safe_import("runtime.drivers.accessibility.semantic")
        )
        self.assertIsNotNone(semantic, "Semantic Parser module missing.")

    def test_07_planner(self):
        planner = safe_import("runtime.planner.planner")
        self.assertIsNotNone(planner, "Planner module missing.")

    def test_08_workflow_executor(self):
        executor = safe_import("runtime.workflow.executor")
        self.assertIsNotNone(executor, "Workflow Executor module missing.")

    def test_09_provider_manager(self):
        manager = safe_import("runtime.providers.manager")
        self.assertIsNotNone(manager, "Provider Manager module missing.")

    def test_10_knowledge_graph(self):
        kg = safe_import("runtime.memory.knowledge_graph")
        self.assertIsNotNone(kg, "Knowledge Graph module missing.")

    def test_11_agent_coordinator(self):
        coordinator = safe_import("runtime.agents.coordinator")
        self.assertIsNotNone(coordinator, "Agent Coordinator module missing.")

    def test_12_plugin_loader(self):
        loader = safe_import("runtime.plugin_loader")
        self.assertIsNotNone(loader, "Plugin Loader module missing.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
