import unittest
import sys
import os
import importlib

# Attempt to load components dynamically to handle structural variations
def safe_import(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None

class TestBroccoliCore(unittest.TestCase):
    def test_01_runtime_startup(self):
        main = safe_import("main")
        self.assertIsNotNone(main, "Runtime startup (main.py) failed to import.")
        
    def test_02_event_bus(self):
        event_bus = safe_import("event_bus")
        self.assertIsNotNone(event_bus, "Event Bus module missing.")
        if hasattr(event_bus, 'EventBus'):
            bus = event_bus.EventBus()
            self.assertTrue(hasattr(bus, 'publish') or hasattr(bus, 'emit'), "EventBus missing publish/emit mechanism.")

    def test_03_scheduler(self):
        scheduler = safe_import("scheduler")
        self.assertIsNotNone(scheduler, "Scheduler module missing.")

    def test_04_governor(self):
        engine = safe_import("governor.engine")
        self.assertIsNotNone(engine, "Governor engine module missing.")

    def test_05_accessibility_driver(self):
        driver = safe_import("drivers.accessibility.driver")
        self.assertIsNotNone(driver, "Accessibility Driver missing.")

    def test_06_semantic_parser(self):
        semantic = safe_import("models.semantic") or safe_import("drivers.accessibility.semantic")
        self.assertIsNotNone(semantic, "Semantic Parser module missing.")

    def test_07_planner(self):
        planner = safe_import("planner.planner")
        self.assertIsNotNone(planner, "Planner module missing.")

    def test_08_workflow_executor(self):
        executor = safe_import("workflow.executor")
        self.assertIsNotNone(executor, "Workflow Executor module missing.")

    def test_09_provider_manager(self):
        manager = safe_import("providers.manager")
        self.assertIsNotNone(manager, "Provider Manager module missing.")

    def test_10_knowledge_graph(self):
        kg = safe_import("memory.knowledge_graph")
        self.assertIsNotNone(kg, "Knowledge Graph module missing.")

    def test_11_agent_coordinator(self):
        coordinator = safe_import("agents.coordinator")
        self.assertIsNotNone(coordinator, "Agent Coordinator module missing.")

    def test_12_plugin_loader(self):
        loader = safe_import("plugin_loader")
        self.assertIsNotNone(loader, "Plugin Loader module missing.")

if __name__ == '__main__':
    unittest.main(verbosity=2)
