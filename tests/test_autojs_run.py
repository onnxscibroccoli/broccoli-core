import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scripts.autojs_run as autojs


class _Result:
    ok = True
    returncode = 0
    combined_output = ""


class AutoJSRunTests(unittest.TestCase):
    def test_missing_payload_fails_fast(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(autojs, "SD", Path(td)):
                with self.assertRaises(FileNotFoundError):
                    autojs.run_js("missing.js", timeout=0.01)

    def test_run_js_uses_canonical_rish_transport_and_observes_output(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sd = root / "autojs"
            ui = root / "ui"
            sd.mkdir()
            ui.mkdir()
            payload = sd / "probe.js"
            marker = ui / "marker.txt"
            payload.write_text("exit();\n", encoding="utf-8")
            commands = []

            class FakeTransport:
                def __init__(self, timeout):
                    self.timeout = timeout

                def run(self, command, timeout=None):
                    commands.append(command)
                    marker.write_text("done", encoding="utf-8")
                    return _Result()

            with patch.object(autojs, "SD", sd), patch.object(autojs, "RishTransport", FakeTransport):
                self.assertTrue(autojs.run_js(payload.name, marker, timeout=0.2))

            self.assertEqual(len(commands), 1)
            self.assertIn("org.autojs.autojs.modify", commands[0])
            self.assertIn("file://", commands[0])


if __name__ == "__main__":
    unittest.main()
