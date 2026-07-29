from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.memory.knowledge_graph import KnowledgeGraph


class FakeBus:
    def __init__(self):
        self.events = []
        self.subscriptions = {}

    def subscribe(self, topic, callback):
        self.subscriptions.setdefault(topic, []).append(callback)

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class KnowledgeGraphIntegrationTest(unittest.TestCase):
    def test_roundtrip_write_read_and_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bus = FakeBus()
            emitted = []

            graph = KnowledgeGraph(
                bus=bus,
                root=root,
                warning_seconds=10,
                critical_seconds=30,
                event_writer=lambda **kw: emitted.append(kw),
            )

            self.assertTrue(graph.verify_roundtrip())
            snap = graph.run_once()

            self.assertIn(snap.status, {"KNOWLEDGE_OK", "KNOWLEDGE_WARNING"})
            self.assertGreaterEqual(snap.node_count, 1)
            self.assertTrue(any(evt[0] == "KNOWLEDGE_WRITE" for evt in bus.events))
            self.assertTrue(any(evt[0] == "KNOWLEDGE_READ" for evt in bus.events))
            self.assertTrue(any(e["event"] == "KNOWLEDGE_HEARTBEAT" or e["event"] == "KNOWLEDGE_WRITE" for e in emitted))

    def test_stale_state_becomes_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            graph = KnowledgeGraph(
                bus=FakeBus(),
                root=root,
                warning_seconds=1,
                critical_seconds=2,
                event_writer=lambda **kw: None,
            )
            graph.last_activity_at = 0
            snap = graph.collect_health()
            self.assertEqual(snap.status, "KNOWLEDGE_CRITICAL")


if __name__ == "__main__":
    unittest.main()
