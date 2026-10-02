import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

import broccoli_device
import broccoli_rish_shell


class _Result:
    returncode = 0
    combined_output = "transport-ok"


class RishCompatibilityTests(unittest.TestCase):
    def test_shell_prefers_canonical_transport(self):
        calls = []

        class FakeTransport:
            def __init__(self, timeout):
                self.timeout = timeout

            def run(self, command, timeout=None):
                calls.append((command, timeout))
                return _Result()

        with patch.object(broccoli_rish_shell, "_transport_class", return_value=FakeTransport):
            rc, out = broccoli_rish_shell.shell("id", timeout=7)

        self.assertEqual((rc, out), (0, "transport-ok"))
        self.assertEqual(calls, [("id", 7)])

    def test_rish_ok_restores_tuple_contract(self):
        evidence = "BROCCOLI_RISH_OK\nuid=2000(shell) gid=2000(shell)\n35\n"
        with patch.object(broccoli_rish_shell, "shell", return_value=(0, evidence)):
            ok, info = broccoli_rish_shell.rish_ok()
        self.assertTrue(ok)
        self.assertIn("uid=2000(shell)", info)

    def test_rish_ok_rejects_empty_zero_exit(self):
        with patch.object(broccoli_rish_shell, "shell", return_value=(0, "")):
            ok, info = broccoli_rish_shell.rish_ok()
        self.assertFalse(ok)
        self.assertEqual(info, "")

    def test_device_ready_exposes_boolean_and_evidence(self):
        with patch.object(broccoli_device, "rish_ok", return_value=(False, "not proven")):
            result = broccoli_device.device_ready()
        self.assertIs(result["rish_ok"], False)
        self.assertEqual(result["rish_info"], "not proven")

    def test_foreground_pkg_reads_shell_output_not_tuple(self):
        output = "mCurrentFocus=Window{abc u0 ai.x.grok/.main.GrokActivity}"
        with patch.object(broccoli_device, "shell", return_value=(0, output)):
            self.assertEqual(broccoli_device.foreground_pkg(), "ai.x.grok")


if __name__ == "__main__":
    unittest.main()
