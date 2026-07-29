from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from runtime.governor.end_to_end_smoke import EndToEndSmoke


class FakeBus:
    def __init__(self):
        self.events = []
        self.subscriptions = {}

    def subscribe(self, topic, callback):
        self.subscriptions.setdefault(topic, []).append(callback)

    def publish(self, topic, payload=None, source="unknown"):
        self.events.append((topic, payload, source))


class FakeBootstrapSnapshot:
    def __init__(self, status="BOOTSTRAP_OK"):
        self.status = status

    def to_dict(self):
        return {"status": self.status}


class FakeBootstrap:
    instances = 0
    verify_calls = 0
    run_calls = 0

    def __init__(self, **kwargs):
        FakeBootstrap.instances += 1

    def verify_bootstrap(self):
        FakeBootstrap.verify_calls += 1
        return {
            "knowledge_roundtrip": True,
            "adaptive_verification": {"status": "ADAPTIVE_OK"},
        }

    def run_once(self):
        FakeBootstrap.run_calls += 1
        return FakeBootstrapSnapshot("BOOTSTRAP_OK")


class EndToEndSmokeTest(unittest.TestCase):
    def test_smoke_reports_ok_when_bootstrap_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            emitted = []
            bus = FakeBus()

            with patch("runtime.governor.end_to_end_smoke.SystemBootstrapOrchestrator", FakeBootstrap):
                smoke = EndToEndSmoke(
                    bus=bus,
                    root=root,
                    event_writer=lambda **kw: emitted.append(kw),
                )
                snapshot = smoke.run()

            self.assertEqual(snapshot.status, "SMOKE_OK")
            self.assertTrue(snapshot.verification_ok)
            self.assertEqual(snapshot.bootstrap_status, "BOOTSTRAP_OK")
            self.assertTrue(any(evt[0] == "SMOKE_OK" for evt in bus.events))
            self.assertTrue(any(e["event"] == "SMOKE_OK" for e in emitted))
            self.assertEqual(FakeBootstrap.verify_calls, 1)
            self.assertEqual(FakeBootstrap.run_calls, 1)

    def test_strict_failure_would_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            class FakeBadBootstrap(FakeBootstrap):
                def verify_bootstrap(self):
                    return {
                        "knowledge_roundtrip": False,
                        "adaptive_verification": {"status": "ADAPTIVE_CRITICAL"},
                    }

            with patch("runtime.governor.end_to_end_smoke.SystemBootstrapOrchestrator", FakeBadBootstrap):
                smoke = EndToEndSmoke(bus=FakeBus(), root=root, event_writer=lambda **kw: None)
                snapshot = smoke.run()

            self.assertIn(snapshot.status, {"SMOKE_WARNING", "SMOKE_CRITICAL"})


if __name__ == "__main__":
    unittest.main()
