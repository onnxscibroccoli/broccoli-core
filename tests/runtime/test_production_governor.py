from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from runtime.governor.production_governor import ProductionGovernor


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class ProductionGovernorTest(unittest.TestCase):
    def _write_artifact(self, root: Path, name: str, age_seconds: int = 0, payload=None) -> Path:
        processed = root / "runtime" / "event_bus" / "processed"
        processed.mkdir(parents=True, exist_ok=True)
        path = processed / name
        path.write_text(json.dumps(payload or {"status": "OK"}, indent=2))
        ts = time.time() - age_seconds
        path.touch()
        import os
        os.utime(path, (ts, ts))
        return path

    def test_all_fresh_artifacts_produce_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, payload in (
                ("runtime_health_1.json", {"status": "RUNTIME_OK"}),
                ("recovery_1.json", {"event": "RECOVERY_FINISHED"}),
                ("accessibility_1.json", {"status": "ACCESSIBILITY_OK"}),
                ("workflow_1.json", {"status": "WORKFLOW_OK"}),
                ("scheduler_1.json", {"status": "SCHEDULER_OK"}),
                ("knowledge_1.json", {"status": "KNOWLEDGE_OK"}),
                ("metrics_1.json", {"status": "METRICS_OK"}),
                ("dashboard_1.json", {"status": "DASHBOARD_OK"}),
            ):
                self._write_artifact(root, name, age_seconds=1, payload=payload)

            bus = FakeBus()
            emitted = []
            gov = ProductionGovernor(
                bus=bus,
                root=root,
                warning_seconds=10,
                critical_seconds=30,
                event_writer=lambda **kw: emitted.append(kw),
            )

            snap = gov.run_once()

            self.assertEqual(snap.status, "PRODUCTION_OK")
            self.assertTrue(any(evt[0] == "PRODUCTION_OK" for evt in bus.events))
            self.assertTrue(any(e["event"] == "PRODUCTION_OK" for e in emitted))
            self.assertTrue(snap.components)

    def test_stale_required_artifact_triggers_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifact(root, "runtime_health_1.json", age_seconds=999, payload={"status": "RUNTIME_OK"})
            self._write_artifact(root, "recovery_1.json", age_seconds=1, payload={"event": "RECOVERY_FINISHED"})
            self._write_artifact(root, "accessibility_1.json", age_seconds=1, payload={"status": "ACCESSIBILITY_OK"})
            self._write_artifact(root, "workflow_1.json", age_seconds=1, payload={"status": "WORKFLOW_OK"})
            self._write_artifact(root, "scheduler_1.json", age_seconds=1, payload={"status": "SCHEDULER_OK"})
            self._write_artifact(root, "knowledge_1.json", age_seconds=1, payload={"status": "KNOWLEDGE_OK"})
            self._write_artifact(root, "metrics_1.json", age_seconds=1, payload={"status": "METRICS_OK"})

            bus = FakeBus()
            gov = ProductionGovernor(
                bus=bus,
                root=root,
                warning_seconds=10,
                critical_seconds=30,
                event_writer=lambda **kw: None,
            )

            snap = gov.run_once()

            self.assertEqual(snap.status, "PRODUCTION_CRITICAL")
            self.assertTrue(any(evt[0] in {"PRODUCTION_CRITICAL", "PRODUCTION_RECOVERY_REQUIRED"} for evt in bus.events))


if __name__ == "__main__":
    unittest.main()
