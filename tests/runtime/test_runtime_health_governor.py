from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from runtime.governor.runtime_health_governor import RuntimeHealthGovernor


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class RuntimeHealthGovernorTest(unittest.TestCase):
    def _touch(self, path: Path, content: str = "x") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        now = time.time()
        path.touch()
        # Ensure the file is fresh enough for the freshness checks.
        Path(path).utime if hasattr(Path, "utime") else None

    def test_runtime_ok_when_required_files_are_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runtime" / "event_bus" / "processed").mkdir(parents=True, exist_ok=True)
            (root / ".drive_sync").mkdir(parents=True, exist_ok=True)

            self._touch(root / "runtime" / "event_bus" / "processed" / "repo_1.json", '{"ok": true}')
            self._touch(root / "runtime" / "event_bus" / "processed" / "event_1.json", '{"ok": true}')
            self._touch(root / ".drive_sync" / "sync.log", "healthy")

            bus = FakeBus()
            emitted = []
            governor = RuntimeHealthGovernor(
                bus=bus,
                root=root,
                event_writer=lambda **kw: emitted.append(kw),
            )

            snapshot = governor.run_once()

            self.assertEqual(snapshot.overall_status, "RUNTIME_OK")
            self.assertTrue(any(e["event"] == "RUNTIME_OK" for e in emitted))
            self.assertTrue(bus.events)

    def test_missing_required_drive_sync_is_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "runtime" / "event_bus" / "processed").mkdir(parents=True, exist_ok=True)

            self._touch(root / "runtime" / "event_bus" / "processed" / "repo_1.json", '{"ok": true}')
            self._touch(root / "runtime" / "event_bus" / "processed" / "event_1.json", '{"ok": true}')

            governor = RuntimeHealthGovernor(
                bus=FakeBus(),
                root=root,
                event_writer=lambda **kw: None,
            )

            snapshot = governor.run_once()

            self.assertIn(snapshot.overall_status, {"COMPONENT_DOWN", "HEALTH_CRITICAL"})
            drive = next(c for c in snapshot.components if c.name == "drive_sync")
            self.assertFalse(drive.healthy)


if __name__ == "__main__":
    unittest.main()
