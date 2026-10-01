import json
import subprocess
import sys
import unittest


class AndroidActionCliTests(unittest.TestCase):
    def run_cli(self, payload):
        proc = subprocess.run(
            [sys.executable, "tools/android_action_cli.py"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
        )
        return proc

    def test_unknown_shell_is_rejected(self):
        proc = self.run_cli({"action": "shell", "command": "id"})
        self.assertEqual(proc.returncode, 2)
        body = json.loads(proc.stdout)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "ValueError")

    def test_invalid_json_contract(self):
        proc = subprocess.run(
            [sys.executable, "tools/android_action_cli.py"],
            input="[]",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertFalse(json.loads(proc.stdout)["ok"])


if __name__ == "__main__":
    unittest.main()
