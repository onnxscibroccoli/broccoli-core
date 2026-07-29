from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.memory.knowledge_graph import KnowledgeGraph
from runtime.planner.adaptive import AdaptivePlanner


class FakeBus:
    def __init__(self):
        self.events = []
        self.subscriptions = {}

    def subscribe(self, topic, callback):
        self.subscriptions.setdefault(topic, []).append(callback)

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class AdaptivePlannerTest(unittest.TestCase):
    def test_plan_and_feedback_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bus = FakeBus()
            emitted = []

            kg = KnowledgeGraph(
                bus=bus,
                root=root,
                warning_seconds=10,
                critical_seconds=30,
                event_writer=lambda **kw: emitted.append(kw),
            )
            planner = AdaptivePlanner(
                bus=bus,
                root=root,
                knowledge_graph=kg,
                warning_seconds=10,
                critical_seconds=30,
                event_writer=lambda **kw: emitted.append(kw),
            )

            plan = planner.plan("integrate knowledge graph", {"priority": "high"})
            self.assertIn("plan_id", plan)
            self.assertGreaterEqual(len(plan["steps"]), 4)

            feedback = planner.record_feedback(
                plan_id=plan["plan_id"],
                step_id=plan["steps"][0]["step_id"],
                success=True,
                feedback="reused prior pattern successfully",
                context={"result": "ok"},
            )
            self.assertTrue(feedback["success"])

            snap = planner.run_once()
            self.assertIn(snap.status, {"ADAPTIVE_OK", "ADAPTIVE_WARNING"})
            self.assertTrue(any(evt[0] == "ADAPTIVE_PLAN_CREATED" for evt in bus.events))
            self.assertTrue(any(evt[0] == "ADAPTIVE_FEEDBACK" for evt in bus.events))
            self.assertTrue(any(evt[0] in {"ADAPTIVE_LEARNED", "ADAPTIVE_OK"} for evt in bus.events))
            self.assertTrue((root / "runtime" / "event_bus" / "processed" / "knowledge_graph_state.json").exists())

    def test_stale_planner_becomes_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bus = FakeBus()
            kg = KnowledgeGraph(bus=bus, root=root, event_writer=lambda **kw: None)
            planner = AdaptivePlanner(
                bus=bus,
                root=root,
                knowledge_graph=kg,
                warning_seconds=1,
                critical_seconds=2,
                event_writer=lambda **kw: None,
            )

            planner.last_plan_at = 0
            planner.last_feedback_at = 0
            kg.last_activity_at = 0

            snap = planner.collect_health()
            self.assertEqual(snap.status, "ADAPTIVE_CRITICAL")


if __name__ == "__main__":
    unittest.main()
