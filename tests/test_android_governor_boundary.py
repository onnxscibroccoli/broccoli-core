import io
import json
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from tools.actions import ActionDispatcher
from tools.android_action_cli import main as cli_main
from tools.android_action_policy import (
    ActionRejected, PolicyBlocked, MATCH_FIELDS, validate_action,
)
from tests.android_policy_fixture import FixtureAllow, with_test_authorization


class FakeBackend:
    def __init__(self):
        self.calls = []

    def run(self, command):
        self.calls.append(command)
        return command


class Escalate:
    def authorize(self, action):
        return {"decision": "ESCALATE"}


class Mismatched:
    def authorize(self, action):
        decision = FixtureAllow().authorize(action)
        decision["device_id"] = "another-device"
        return decision


class AndroidGovernorBoundaryTests(unittest.TestCase):
    def test_no_policy_blocks_device_mutation(self):
        backend = FakeBackend()
        with self.assertRaises(PolicyBlocked):
            ActionDispatcher(backend).execute(with_test_authorization({
                "action": "tap", "display_id": 0, "x": 10, "y": 20,
            }))
        self.assertEqual(backend.calls, [])

    def test_client_confirm_does_not_substitute_for_authorization(self):
        backend = FakeBackend()
        with self.assertRaises(PolicyBlocked):
            ActionDispatcher(backend).execute(with_test_authorization({
                "action": "app.stop", "confirm": True, "package": "com.example.app",
            }))
        self.assertEqual(backend.calls, [])

    def test_shared_storage_ui_dump_requires_policy(self):
        backend = FakeBackend()
        with self.assertRaises(PolicyBlocked):
            ActionDispatcher(backend).execute(with_test_authorization({"action": "ui.dump"}))
        self.assertEqual(backend.calls, [])

    def test_escalate_never_executes(self):
        backend = FakeBackend()
        with self.assertRaises(PolicyBlocked):
            ActionDispatcher(backend, authorizer=Escalate()).execute(
                with_test_authorization({"action": "tap", "display_id": 0, "x": 1, "y": 2})
            )
        self.assertEqual(backend.calls, [])

    def test_approval_must_match_device_identity(self):
        backend = FakeBackend()
        with self.assertRaises(PolicyBlocked):
            ActionDispatcher(backend, authorizer=Mismatched()).execute(
                with_test_authorization({"action": "keyevent", "display_id": 0, "key": "HOME"})
            )
        self.assertEqual(backend.calls, [])

    def test_trusted_test_policy_allows_exactly_one_mutation(self):
        backend = FakeBackend()
        ActionDispatcher(backend, authorizer=FixtureAllow()).execute(
            with_test_authorization({"action": "tap", "display_id": 0, "x": 1, "y": 2})
        )
        self.assertEqual(backend.calls, ["input -d 0 tap 1 2"])

    def test_legacy_read_only_inspection_still_works_without_policy(self):
        backend = FakeBackend()
        ActionDispatcher(backend).execute({"action": "package.inspect", "package": "com.example.app"})
        self.assertEqual(len(backend.calls), 1)

    def test_unexpected_schema_field_rejected_before_transport(self):
        backend = FakeBackend()
        with self.assertRaises(ActionRejected):
            ActionDispatcher(backend, authorizer=FixtureAllow()).execute(
                with_test_authorization({
                    "action": "tap", "display_id": 0, "x": 1, "y": 2, "command": "id",
                })
            )
        self.assertEqual(backend.calls, [])

    def test_coordinates_require_actual_integers_and_bounds(self):
        for value in (True, 1.5, -1, 16384, "10"):
            with self.subTest(value=value):
                with self.assertRaises(ActionRejected):
                    validate_action(with_test_authorization({
                        "action": "tap", "display_id": 0, "x": value, "y": 2,
                    }))

    def test_swipe_point_shapes_reject_extra_items(self):
        with self.assertRaises(ActionRejected):
            validate_action(with_test_authorization({
                "action": "swipe", "display_id": 0,
                "start": [1, 2, 3], "end": [4, 5],
            }))

    def test_text_controls_rejected(self):
        with self.assertRaises(ActionRejected):
            validate_action(with_test_authorization({
                "action": "text", "display_id": 0, "text": "line\nnext",
            }))

    def test_expired_envelope_rejected_before_policy(self):
        backend = FakeBackend()
        action = with_test_authorization({"action": "tap", "display_id": 0, "x": 1, "y": 2})
        action["created_at"] = (datetime.now(timezone.utc) - timedelta(minutes=8)).isoformat()
        action["expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=7)).isoformat()
        with self.assertRaises(ActionRejected):
            ActionDispatcher(backend, authorizer=FixtureAllow()).execute(action)
        self.assertEqual(backend.calls, [])

    def test_cli_rejects_duplicate_json_object_keys(self):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO('{"action":"device.identity","action":"tap"}')):
            with redirect_stdout(output):
                code = cli_main()
        self.assertEqual(code, 2)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["message"], "duplicate action JSON key")

    def test_cli_rejects_oversize_payload_before_transport(self):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO("x" * 16385)):
            with redirect_stdout(output):
                code = cli_main()
        self.assertEqual(code, 2)
        self.assertIn("size limit", output.getvalue())

    def test_cli_cannot_mutate_by_self_proclaiming_approval(self):
        action = with_test_authorization({"action": "tap", "display_id": 0, "x": 1, "y": 2})
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(action))):
            with redirect_stdout(output):
                code = cli_main()
        self.assertEqual(code, 2)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload.get("status"), "BLOCKED_BY_POLICY")


if __name__ == "__main__":
    unittest.main()
