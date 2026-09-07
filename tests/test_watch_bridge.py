import os
import tempfile
import unittest
from pathlib import Path

from runtime.surface.factory import open_surface
from runtime.watchme.bridge import WatchBridge
from runtime.watchme.record import WatchSession
from runtime.watchme.replay import replay_from_text


class BridgeTests(unittest.TestCase):
    def test_focus_and_password_redact(self):
        ses = WatchSession("demo")
        br = WatchBridge(ses)
        br.on_event(
            {
                "event_type": "FOCUS_CHANGED",
                "stable_id": "e1",
                "payload": {"text": "Email", "role": "email"},
            }
        )
        br.on_event(
            {
                "event_type": "CONTENT_CHANGED",
                "payload": {"password": True, "text": "hunter2", "role": "password"},
            }
        )
        self.assertGreaterEqual(br.accepted, 2)
        self.assertNotIn("hunter2", str(ses.steps))

    def test_factory_falls_back_to_memory(self):
        surf, kind = open_surface()
        self.assertEqual(kind, "memory")
        self.assertTrue(surf.create("x").ok)


class ReplayTextTests(unittest.TestCase):
    def test_no_match(self):
        with tempfile.TemporaryDirectory() as td:
            os.environ["BROCCOLI_WATCHME"] = str(Path(td) / "c.jsonl")
            try:
                out = replay_from_text("run task totally-missing-zzz")
                self.assertFalse(out["ok"])
                self.assertEqual(out["code"], "no_match")
            finally:
                os.environ.pop("BROCCOLI_WATCHME", None)


if __name__ == "__main__":
    unittest.main()
