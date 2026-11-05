"""Offline timeout regressions; no Android device is used."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from tools.android_transport import RishTransport
from tools import android_action_cli


class TransportTimeoutTests(unittest.TestCase):
    def test_timeout_after_side_effect_is_unknown_and_not_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "effects"
            wrapper = Path(directory) / "wrapper.sh"
            wrapper.write_text(
                'printf "effect\\n" >> "$1"\n'
                'printf "sensitive-output"\n'
                'printf "sensitive-error" >&2\n'
                'exec sleep 5\n'
            )
            with patch.dict(os.environ, {"BOOTCLASSPATH": "offline-test"}):
                try:
                    result = RishTransport(str(wrapper), timeout=0.3).run(str(marker))
                except subprocess.TimeoutExpired:
                    self.fail("timeout escaped instead of preserving unknown outcome")
            self.assertEqual(marker.read_text().splitlines(), ["effect"])
            self.assertFalse(result.ok)
            self.assertEqual(result.status, "OUTCOME_UNKNOWN")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("sensitive", result.stderr)
            self.assertNotIn(str(marker), result.stderr)

    def test_bridge_timeout_preserves_unknown_outcome_without_retry(self):
        calls = []
        def unavailable_completion(*args, **kwargs):
            calls.append(args)
            raise TimeoutError("sensitive remote command")
        with patch.dict(os.environ, {"BOOTCLASSPATH": ""}):
            with patch("tools.android_transport.termux_bridge_available", return_value=True):
                with patch("tools.android_transport.termux_bridge_run", side_effect=unavailable_completion):
                    try:
                        result = RishTransport().run("input text sensitive")
                    except TimeoutError:
                        self.fail("bridge timeout escaped instead of preserving unknown outcome")
        self.assertEqual(len(calls), 1)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "OUTCOME_UNKNOWN")
        self.assertNotIn("sensitive", result.combined_output)

    def test_cli_timeout_is_redacted_and_machine_readable(self):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO('{"action": "device.identity"}')):
            with patch.dict(os.environ, {"BOOTCLASSPATH": "offline-test"}):
                with patch("tools.android_transport.subprocess.run",
                           side_effect=subprocess.TimeoutExpired(
                               ["bash", "wrapper", "sensitive-command"], 1,
                               output="sensitive-output", stderr="sensitive-error")):
                    with contextlib.redirect_stdout(output):
                        rc = android_action_cli.main()
        payload = json.loads(output.getvalue())
        self.assertNotEqual(rc, 0)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload.get("status"), "OUTCOME_UNKNOWN")
        self.assertNotIn("sensitive", output.getvalue())


if __name__ == "__main__":
    unittest.main()
