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

    def test_smoke_retries_transient_transport_error_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sd = root / "autojs"
            ui = root / "ui"
            calls = []
            token = "fedcba9876543210"

            def fake_run(name, wait_out=None, timeout=20.0):
                calls.append((name, Path(wait_out), timeout))
                if len(calls) == 1:
                    raise autojs.AutoJSError("Server is not running")
                Path(wait_out).write_text(
                    f"BROCCOLI_AUTOJS_OK {token} 2026-10-02T00:00:00Z",
                    encoding="utf-8",
                )
                return True

            with (
                patch.object(autojs, "SD", sd),
                patch.object(autojs, "UI", ui),
                patch.object(autojs.secrets, "token_hex", return_value=token),
                patch.object(autojs, "run_js", side_effect=fake_run),
                patch.object(autojs.time, "sleep"),
            ):
                value = autojs.smoke(timeout=0.01, attempts=2)

            self.assertTrue(value.startswith(f"BROCCOLI_AUTOJS_OK {token} "))
            self.assertEqual(len(calls), 2)

    def test_smoke_retries_transient_cold_start_once(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sd = root / "autojs"
            ui = root / "ui"
            calls = []
            token = "0123456789abcdef"

            def fake_run(name, wait_out=None, timeout=20.0):
                calls.append((name, Path(wait_out), timeout))
                if len(calls) == 1:
                    return False
                Path(wait_out).write_text(
                    f"BROCCOLI_AUTOJS_OK {token} 2026-10-02T00:00:00Z",
                    encoding="utf-8",
                )
                return True

            with (
                patch.object(autojs, "SD", sd),
                patch.object(autojs, "UI", ui),
                patch.object(autojs.secrets, "token_hex", return_value=token),
                patch.object(autojs, "run_js", side_effect=fake_run),
                patch.object(autojs.time, "sleep"),
            ):
                value = autojs.smoke(timeout=0.01, attempts=2)

            self.assertTrue(value.startswith(f"BROCCOLI_AUTOJS_OK {token} "))
            self.assertEqual(len(calls), 2)
            self.assertFalse((sd / f"_broccoli_smoke_{token}.js").exists())
            self.assertFalse((ui / f"autojs_smoke_{token}.txt").exists())


if __name__ == "__main__":
    unittest.main()
