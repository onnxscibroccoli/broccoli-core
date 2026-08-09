from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.governor.system_bootstrap import SystemBootstrapOrchestrator


class FakeBus:
    def __init__(self):
        self.events = []
        self.subscriptions = {}

    def subscribe(self, topic, callback):
        self.subscriptions.setdefault(topic, []).append(callback)

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class FakeSnapshot:
    def __init__(self, status="OK"):
        self.status = status

    def to_dict(self):
        return {"status": self.status}


class FakeRecovery:
    def __init__(self, **kwargs):
        self.calls = 0

    def run_once(self):
        self.calls += 1
        return 0


class FakeGovernor:
    def __init__(self, status="OK", **kwargs):
        self.status = status
        self.calls = 0

    def run_once(self):
        self.calls += 1
        return FakeSnapshot(self.status)


class FakeKnowledge:
    def __init__(self, **kwargs):
        self.calls = 0

    def run_once(self):
        self.calls += 1
        return FakeSnapshot("KNOWLEDGE_OK")

    def verify_roundtrip(self):
        return True


class FakeAdaptive:
    def __init__(self, knowledge_graph=None, **kwargs):
        self.calls = 0
        self.knowledge_graph = knowledge_graph

    def run_once(self):
        self.calls += 1
        return FakeSnapshot("ADAPTIVE_OK")

    def verify_integration(self):
        return {"status": "ADAPTIVE_OK", "verified": True}


class BootstrapOrchestratorTest(unittest.TestCase):
    @patch("runtime.governor.system_bootstrap.RuntimeHealthGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.RecoveryManager", FakeRecovery)
    @patch("runtime.governor.system_bootstrap.AccessibilityGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.WorkflowGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.SchedulerGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.KnowledgeGraph", FakeKnowledge)
    @patch("runtime.governor.system_bootstrap.AdaptivePlanner", FakeAdaptive)
    @patch("runtime.governor.system_bootstrap.MetricsGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.UnifiedMetricsDashboard", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.ProductionGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.GovernorSupervisor", FakeGovernor)
    def test_bootstrap_runs_all_components(self, *mocks):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bus = FakeBus()
            emitted = []
            orchestrator = SystemBootstrapOrchestrator(
                bus=bus,
                root=root,
                event_writer=lambda **kw: emitted.append(kw),
                warning_seconds=10,
                critical_seconds=30,
            )

            snapshot = orchestrator.run_once()

            self.assertIn(snapshot.status, {"BOOTSTRAP_OK", "BOOTSTRAP_WARNING", "BOOTSTRAP_CRITICAL"})
            self.assertEqual(len(snapshot.components), 11)
            self.assertTrue(any(evt[0].startswith("BOOTSTRAP") for evt in bus.events))
            self.assertTrue(emitted)

    @patch("runtime.governor.system_bootstrap.RuntimeHealthGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.RecoveryManager", FakeRecovery)
    @patch("runtime.governor.system_bootstrap.AccessibilityGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.WorkflowGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.SchedulerGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.KnowledgeGraph", FakeKnowledge)
    @patch("runtime.governor.system_bootstrap.AdaptivePlanner", FakeAdaptive)
    @patch("runtime.governor.system_bootstrap.MetricsGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.UnifiedMetricsDashboard", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.ProductionGovernor", FakeGovernor)
    @patch("runtime.governor.system_bootstrap.GovernorSupervisor", FakeGovernor)
    def test_verify_bootstrap(self, *mocks):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orchestrator = SystemBootstrapOrchestrator(
                bus=FakeBus(),
                root=root,
                event_writer=lambda **kw: None,
            )

            result = orchestrator.verify_bootstrap()
            self.assertTrue(result["knowledge_roundtrip"])
            self.assertEqual(result["adaptive_verification"]["status"], "ADAPTIVE_OK")


if __name__ == "__main__":
    unittest.main()
