from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from runtime.governor.scheduler_governor import SchedulerGovernor


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


class SchedulerGovernorTest(unittest.TestCase):
    def test_recent_tick_is_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bus = FakeBus()
            emitted = []
            gov = SchedulerGovernor(
                bus=bus,
                root=root,
                warning_seconds=5,
                critical_seconds=10,
                event_writer=lambda **kw: emitted.append(kw),
            )

            gov._on_scheduler_event(FakeEvent("TICK", {"tick": 1}))
            snap = gov.run_once()

            self.assertEqual(snap.status, "SCHEDULER_OK")
            self.assertTrue(any(evt[0] == "SCHEDULER_OK" for evt in bus.events))
            self.assertTrue(any(e["event"] == "SCHEDULER_OK" for e in emitted))

    def test_stale_scheduler_becomes_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bus = FakeBus()
            gov = SchedulerGovernor(
                bus=bus,
                root=root,
                warning_seconds=1,
                critical_seconds=2,
                event_writer=lambda **kw: None,
            )

            gov.last_event_at = time.time() - 999
            gov.last_event_topic = "TICK"

            snap = gov.run_once()
            self.assertEqual(snap.status, "SCHEDULER_CRITICAL")
            self.assertTrue(any(evt[0] == "SCHEDULER_CRITICAL" for evt in bus.events))


if __name__ == "__main__":
    unittest.main()
