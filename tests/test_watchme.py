import json
import tempfile
import unittest
from pathlib import Path

from runtime.watchme.catalog import WatchCatalog
from runtime.watchme.record import WatchSession, redact_value


class WatchMeTests(unittest.TestCase):
    def test_redacts_passwords(self):
        self.assertEqual(redact_value("password", "hunter2"), "[REDACTED]")
        self.assertEqual(redact_value("composer", "hello"), "hello")

    def test_catalog_search_and_authorized_replay(self):
        with tempfile.TemporaryDirectory() as td:
            cat = WatchCatalog(Path(td) / "c.jsonl")
            demo = cat.record_and_save(
                "toggle flashlight",
                [{"action": "tap", "role": "quick-settings", "text": "Flashlight"}],
                authorize=True,
            )
            hits = cat.search("flashlight")
            self.assertEqual(len(hits), 1)
            self.assertTrue(hits[0]["authorized"])
            result = cat.replay(demo["id"])
            self.assertTrue(result["ok"])
            self.assertTrue(result["prior_auth"])

    def test_unauthorized_replay_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            cat = WatchCatalog(Path(td) / "c.jsonl")
            demo = cat.record_and_save(
                "private",
                [{"action": "tap", "role": "x", "text": "x"}],
                authorize=False,
            )
            result = cat.replay(demo["id"])
            self.assertFalse(result["ok"])
            self.assertEqual(result["code"], "not_authorized")

    def test_ingest_skips_password_text(self):
        ses = WatchSession("login-screen")
        ses.ingest_accessibility(
            [
                {"action": "tap", "text": "Email", "role": "email"},
                {"action": "input", "text": "secret", "password": True, "role": "password"},
            ]
        )
        blob = json.dumps(ses.steps)
        self.assertNotIn("secret", blob)
        self.assertTrue(any(s["action"] == "focus" for s in ses.steps))


class SurfaceSmoke(unittest.TestCase):
    def test_memory_surface_import(self):
        from runtime.surface import MemorySurface

        s = MemorySurface()
        self.assertTrue(s.create("demo").ok)


if __name__ == "__main__":
    unittest.main()
