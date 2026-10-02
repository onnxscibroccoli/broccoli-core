import os
import unittest
from unittest.mock import patch

from tools.android_transport import RishTransport, TransportResult


class AndroidTransportTests(unittest.TestCase):
    def test_reduced_android_context_uses_termux_bridge_without_direct_rish(self):
        with patch.dict(os.environ, {"BOOTCLASSPATH": ""}, clear=False):
            with patch("tools.android_transport.termux_bridge_available", return_value=True):
                with patch("tools.android_transport.termux_bridge_run", return_value=(0, "uid=2000(shell)\\n", "")) as run:
                    with patch("tools.android_transport.subprocess.run") as direct:
                        result = RishTransport(timeout=7).run("id")
        self.assertEqual(result, TransportResult(0, "uid=2000(shell)\\n", ""))
        run.assert_called_once()
        direct.assert_not_called()
        self.assertIn("rish_run.sh", run.call_args.args[0])

    def test_interactive_context_keeps_direct_canonical_wrapper(self):
        with patch.dict(os.environ, {"BOOTCLASSPATH": "framework.jar"}, clear=False):
            with patch("tools.android_transport.termux_bridge_run") as bridge:
                with patch("tools.android_transport.subprocess.run", return_value=type("P", (), {"returncode": 0, "stdout": "ok", "stderr": ""})()) as direct:
                    result = RishTransport(timeout=7).run("id")
        self.assertEqual(result.returncode, 0)
        direct.assert_called_once()
        bridge.assert_not_called()


if __name__ == "__main__":
    unittest.main()
