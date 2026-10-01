import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUPERVISOR = ROOT / "bin" / "broccoli-supervisor"


class SupervisorContractTests(unittest.TestCase):
    def test_supervisor_exists_and_is_bash(self):
        text = SUPERVISOR.read_text()
        self.assertTrue(text.startswith("#!/data/data/com.termux/files/usr/bin/bash"))
        self.assertIn("set -euo pipefail", text)

    def test_singleton_lock_is_atomic(self):
        text = SUPERVISOR.read_text()
        self.assertIn('mkdir "$LOCK_DIR"', text)
        self.assertIn("ALREADY_RUNNING supervisor_pid=", text)

    def test_child_identity_is_verified(self):
        text = SUPERVISOR.read_text()
        self.assertIn("runtime-supervisor.child.pid", text)
        self.assertIn('"$ROOT/runtime/main.py"', text)
        self.assertIn("find_child", text)

    def test_wake_lock_is_requested(self):
        text = SUPERVISOR.read_text()
        self.assertIn("termux-wake-lock", text)


if __name__ == "__main__":
    unittest.main()
