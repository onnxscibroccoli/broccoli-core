"""Offline-only policy fixture. Never import this test authorizer in runtime code."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from tools.actions import ActionDispatcher
from tools.android_action_policy import MATCH_FIELDS, MUTATING_ACTIONS


def with_test_authorization(action):
    normalized = dict(action)
    if normalized.get("action") not in MUTATING_ACTIONS:
        return normalized
    now = datetime.now(timezone.utc)
    normalized.update({
        "principal_id": "test-principal",
        "device_id": "test-device",
        "operation_id": "test-operation",
        "request_id": "test-request",
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=2)).isoformat(),
        "policy_version": "test-v1",
        "authorization_reference": "fixture/allow",
    })
    return normalized


class FixtureAllow:
    def authorize(self, action):
        return {"decision": "ALLOW", **{key: action[key] for key in MATCH_FIELDS}}


class AuthorizedDispatcher(ActionDispatcher):
    """Preserve existing action-command assertions with a bound test-only policy."""

    def __init__(self, backend):
        super().__init__(backend, authorizer=FixtureAllow())

    def execute(self, action):
        return super().execute(with_test_authorization(action))
