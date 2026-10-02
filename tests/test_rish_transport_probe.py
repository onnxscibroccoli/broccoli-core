import unittest

from tools.android_transport import TransportResult
from tools.rish_transport_probe import (
    build_probe_command,
    run_probe,
    validate_output_path,
)


class _Backend:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def run(self, command, timeout=None):
        self.calls.append((command, timeout))
        return self.result


class RishTransportProbeTests(unittest.TestCase):
    def test_rejects_private_termux_path(self):
        with self.assertRaises(ValueError):
            validate_output_path("/data/data/com.termux/files/home/proof.txt")

    def test_build_command_creates_and_reads_shared_artifact(self):
        command = build_probe_command(
            "/sdcard/OmniKali/broccoli/proof.txt", "MARKER_123"
        )
        self.assertIn("mkdir -p", command)
        self.assertIn("MARKER_123", command)
        self.assertIn("id >>", command)
        self.assertIn("cat", command)

    def test_pass_requires_marker_and_shell_identity(self):
        marker = "MARKER_ABC"
        backend = _Backend(
            TransportResult(
                0,
                marker + "\nuid=2000(shell) gid=2000(shell)\n35\n",
                "",
            )
        )
        result = run_probe(
            "/sdcard/OmniKali/broccoli/proof.txt",
            transport=backend,
            marker=marker,
        )
        self.assertTrue(result.ok)
        self.assertEqual(len(backend.calls), 1)

    def test_zero_exit_without_target_evidence_is_not_proven(self):
        backend = _Backend(TransportResult(0, "", ""))
        result = run_probe(
            "/sdcard/OmniKali/broccoli/proof.txt",
            transport=backend,
            marker="MARKER_ABC",
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error, "target marker missing")


if __name__ == "__main__":
    unittest.main()
