from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from runtime.governor.metrics_dashboard import UnifiedMetricsDashboard


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class MetricsDashboardTest(unittest.TestCase):
    def _write_artifact(self, root: Path, name: str, age_seconds: int = 0, payload=None) -> Path:
        processed = root / "runtime" / "event_bus" / "processed"
        processed.mkdir(parents=True, exist_ok=True)
        path = processed / name
        path.write_text(json.dumps(payload or {"ok": True}, indent=2))
        ts = time.time() - age_seconds
        path.touch()
        import os
        os.utime(path, (ts, ts))
        return path

    def test_fresh_artifacts_produce_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in (
                "runtime_health_1.json",
                "recovery_1.json",
                "accessibility_1.json",
                "workflow_1.json",
                "scheduler_1.json",
                "knowledge_1.json",
                "metrics_1.json",
            ):
                self._write_artifact(root, name, age_seconds=1)

            bus = FakeBus()
            emitted = []
            dashboard = UnifiedMetricsDashboard(
                bus=bus,
                root=root,
                warning_seconds=10,
                critical_seconds=30,
                event_writer=lambda **kw: emitted.append(kw),
            )

            snap = dashboard.run_once()

            self.assertEqual(snap.status, "DASHBOARD_OK")
            self.assertTrue(any(evt[0] == "DASHBOARD_OK" for evt in bus.events))
            self.assertTrue(any(e["event"] == "DASHBOARD_OK" for e in emitted))
            self.assertTrue(snap.components)

    def test_stale_artifact_causes_warning_or_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_artifact(root, "runtime_health_1.json", age_seconds=999)
            self._write_artifact(root, "recovery_1.json", age_seconds=1)
            self._write_artifact(root, "accessibility_1.json", age_seconds=1)
            self._write_artifact(root, "workflow_1.json", age_seconds=1)
            self._write_artifact(root, "scheduler_1.json", age_seconds=1)
            self._write_artifact(root, "knowledge_1.json", age_seconds=1)
            self._write_artifact(root, "metrics_1.json", age_seconds=1)

            bus = FakeBus()
            dashboard = UnifiedMetricsDashboard(
                bus=bus,
                root=root,
                warning_seconds=10,
                critical_seconds=30,
                event_writer=lambda **kw: None,
            )

            snap = dashboard.run_once()

            self.assertIn(snap.status, {"DASHBOARD_WARNING", "DASHBOARD_CRITICAL"})
            self.assertTrue(any(evt[0] in {"DASHBOARD_WARNING", "DASHBOARD_CRITICAL"} for evt in bus.events))


if __name__ == "__main__":
    unittest.main()
