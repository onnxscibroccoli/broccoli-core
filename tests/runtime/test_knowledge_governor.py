from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from runtime.governor.knowledge_governor import KnowledgeGovernor


class FakeEvent:
    def __init__(self, topic, payload=None):
        self.topic = topic
        self.payload = payload or {}


class FakeBus:
    def __init__(self):
        self.events = []
        self.subscriptions = {}

    def subscribe(self, topic, callback):
        self.subscriptions.setdefault(topic, []).append(callback)

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class KnowledgeGovernorTest(unittest.TestCase):
    def test_recent_knowledge_event_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bus = FakeBus()
            emitted = []
            gov = KnowledgeGovernor(
                bus=bus,
                root=root,
                warning_seconds=5,
                critical_seconds=10,
                event_writer=lambda **kw: emitted.append(kw),
            )

            gov._on_knowledge_event(FakeEvent("KNOWLEDGE_WRITE", {"key": "alpha"}))
            snap = gov.run_once()

            self.assertEqual(snap.status, "KNOWLEDGE_OK")
            self.assertTrue(any(evt[0] == "KNOWLEDGE_OK" for evt in bus.events))
            self.assertTrue(any(e["event"] == "KNOWLEDGE_OK" for e in emitted))

    def test_stale_knowledge_event_becomes_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bus = FakeBus()
            gov = KnowledgeGovernor(
                bus=bus,
                root=root,
                warning_seconds=1,
                critical_seconds=2,
                event_writer=lambda **kw: None,
            )

            gov.last_event_at = time.time() - 999
            gov.last_event_topic = "KNOWLEDGE_WRITE"

            snap = gov.run_once()
            self.assertEqual(snap.status, "KNOWLEDGE_CRITICAL")
            self.assertTrue(any(evt[0] == "KNOWLEDGE_CRITICAL" for evt in bus.events))


if __name__ == "__main__":
    unittest.main()
