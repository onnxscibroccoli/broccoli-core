import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.android_action_cli import main


class AndroidActionCliTests(unittest.TestCase):
    def run_cli(self, payload):
        stream = io.StringIO(json.dumps(payload))
        output = io.StringIO()
        with patch("sys.stdin", stream), redirect_stdout(output):
            rc = main()
        return rc, json.loads(output.getvalue())

    def test_unknown_shell_is_rejected(self):
        rc, body = self.run_cli({"action": "shell", "command": "id"})
        self.assertEqual(rc, 2)
        self.assertFalse(body["ok"])
        self.assertEqual(body["error"], "ValueError")

    def test_invalid_json_contract(self):
        stream = io.StringIO("[]")
        output = io.StringIO()
        with patch("sys.stdin", stream), redirect_stdout(output):
            rc = main()
        self.assertEqual(rc, 2)
        self.assertFalse(json.loads(output.getvalue())["ok"])


if __name__ == "__main__":
    unittest.main()
