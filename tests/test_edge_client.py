import os
import unittest
from unittest import mock

from runtime.edge_client import EdgeClient


class TestEdgeClient(unittest.TestCase):
    def test_infer_local_fallback_bluetooth(self):
        c = EdgeClient(base_url="")  # no edge configured
        r = c.infer("turn on bluetooth please")
        self.assertEqual(r["intent"], "toggle_bluetooth")
        self.assertEqual(r["source"], "local")

    def test_infer_local_fallback_reminder(self):
        c = EdgeClient(base_url="")
        r = c.infer("remind me to take my meds")
        self.assertEqual(r["intent"], "set_reminder")

    def test_embed_returns_none_without_edge(self):
        c = EdgeClient(base_url="")
        self.assertIsNone(c.embed("hello"))

    def test_health_not_configured(self):
        c = EdgeClient(base_url="")
        h = c.health()
        self.assertFalse(h["configured"])
        self.assertFalse(h["ready"])

    def test_infer_uses_edge_when_available(self):
        c = EdgeClient(base_url="https://example.test")
        fake = mock.Mock()
        fake.read.return_value = b'{"ok": true, "intent": "toggle_bluetooth", "confidence": 0.9}'
        fake.__enter__ = mock.Mock(return_value=fake)
        fake.__exit__ = mock.Mock(return_value=False)
        with mock.patch("runtime.edge_client.urllib.request.urlopen", return_value=fake):
            r = c.infer("bluetooth")
        self.assertEqual(r["intent"], "toggle_bluetooth")
        self.assertEqual(r["source"], "edge")


if __name__ == "__main__":
    unittest.main()
