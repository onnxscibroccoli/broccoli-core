from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.autonomy.recovery import RecoveryManager


class FakeBus:
    def __init__(self):
        self.events = []
        self.subscriptions = {}

    def subscribe(self, topic, callback):
        self.subscriptions.setdefault(topic, []).append(callback)

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class RecoveryManagerTest(unittest.TestCase):
    def _write_snapshot(self, root: Path, overall_status: str = "HEALTH_CRITICAL") -> None:
        processed = root / "runtime" / "event_bus" / "processed"
        processed.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "timestamp": 1785300000,
            "overall_status": overall_status,
            "summary": overall_status,
            "components": [
                {
                    "name": "repository_health",
                    "required": True,
                    "status": "healthy",
                },
                {
                    "name": "drive_sync",
                    "required": True,
                    "status": "critical",
                    "details": {"reason": "stale"},
                },
            ],
        }
        (processed / "runtime_health_1785300000.json").write_text(json.dumps(snapshot, indent=2))

    def test_recovery_emits_lifecycle_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_snapshot(root)

            bus = FakeBus()
            emitted = []
            manager = RecoveryManager(
                bus=bus,
                root=root,
                event_writer=lambda **kw: emitted.append(kw),
            )

            count = manager.scan_and_recover()

            self.assertGreaterEqual(count, 1)
            self.assertTrue(any(topic == "RECOVERY_STARTED" for topic, _, _ in bus.events))
            self.assertTrue(any(topic == "RECOVERY_FINISHED" for topic, _, _ in bus.events))
            self.assertTrue(any(e["event"] == "RECOVERY_STARTED" for e in emitted))
            self.assertTrue(any(e["event"] == "RECOVERY_FINISHED" for e in emitted))

    def test_runtime_ok_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_snapshot(root, overall_status="RUNTIME_OK")

            manager = RecoveryManager(
                bus=FakeBus(),
                root=root,
                event_writer=lambda **kw: None,
            )

            self.assertEqual(manager.scan_and_recover(), 0)


if __name__ == "__main__":
    unittest.main()
