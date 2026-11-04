"""Validated, fail-closed authorization contract for Android side effects.

A caller-supplied approval flag is never an authorization decision.
Only a trusted in-process governor adapter can produce a bound ALLOW record.
This module does not grant Shizuku, Android, or Termux permissions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any

MUTATING_ACTIONS = frozenset({
    "ui.dump",            # writes a shared-storage artifact
    "package.export",     # writes a package copy
    "app.launch", "app.stop", "tap", "swipe", "text", "keyevent",
})
READ_ONLY_ACTIONS = frozenset({"device.identity", "display.list", "package.inspect"})
ALLOWED_ACTIONS = MUTATING_ACTIONS | READ_ONLY_ACTIONS

ACTION_FIELDS = {
    "device.identity": frozenset(),
    "display.list": frozenset(),
    "ui.dump": frozenset(),
    "package.inspect": frozenset({"package"}),
    "package.export": frozenset({"package"}),
    "app.launch": frozenset({"package"}),
    "app.stop": frozenset({"package", "confirm"}),
    "tap": frozenset({"display_id", "x", "y"}),
    "swipe": frozenset({"display_id", "start", "end", "duration_ms"}),
    "text": frozenset({"display_id", "text"}),
    "keyevent": frozenset({"display_id", "key"}),
}
OPTIONAL_FIELDS = {"swipe": frozenset({"duration_ms"})}
AUTH_FIELDS = frozenset({
    "principal_id", "device_id", "operation_id", "request_id",
    "created_at", "expires_at", "policy_version", "authorization_reference",
})
MATCH_FIELDS = (
    "principal_id", "device_id", "operation_id", "request_id",
    "expires_at", "policy_version", "authorization_reference",
)
IDENTITY = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9:._/-]{0,127}$")
PACKAGE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")
KEYEVENT = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


class ActionRejected(ValueError):
    """Invalid or unsupported command; no device operation dispatched."""


class PolicyBlocked(PermissionError):
    """Governor did not authorize this action and device binding."""


def _required_string(action: dict, key: str, maximum: int = 128) -> str:
    value = action.get(key)
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ActionRejected("invalid field: " + key)
    return value


def _coordinate(value: Any) -> int:
    if type(value) is not int or not (0 <= value <= 16383):
        raise ActionRejected("invalid display coordinate")
    return value


def _timestamp(value: str) -> datetime:
    if not isinstance(value, str) or len(value) > 40:
        raise ActionRejected("invalid authorization timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ActionRejected("invalid authorization timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ActionRejected("authorization timestamp requires timezone")
    return parsed.astimezone(timezone.utc)


def validate_action(action: Any) -> str:
    if not isinstance(action, dict):
        raise ActionRejected("action must be a JSON object")
    name = action.get("action")
    if not isinstance(name, str) or name not in ALLOWED_ACTIONS:
        raise ActionRejected("unknown or disallowed Android action")
    expected = ACTION_FIELDS[name]
    required = expected - OPTIONAL_FIELDS.get(name, frozenset())
    for key in required:
        if key not in action:
            raise ActionRejected("missing action field: " + key)
    allowed = expected | {"action"}
    if name in MUTATING_ACTIONS:
        allowed |= AUTH_FIELDS
    unexpected = set(action) - allowed
    if unexpected:
        raise ActionRejected("unknown action fields")
    if "package" in expected:
        package = _required_string(action, "package", 255)
        if not PACKAGE.fullmatch(package):
            raise ActionRejected("invalid Android package name")
    if name == "app.stop" and action.get("confirm") is not True:
        raise ActionRejected("app.stop requires confirm=true in addition to policy authorization")
    if name in {"tap", "swipe", "text", "keyevent"}:
        display_id = action.get("display_id")
        if type(display_id) is not int or not (0 <= display_id <= 99):
            raise ActionRejected("invalid display identifier")
    if name == "tap":
        _coordinate(action.get("x"))
        _coordinate(action.get("y"))
    if name == "swipe":
        for key in ("start", "end"):
            point = action.get(key)
            if not isinstance(point, list) or len(point) != 2:
                raise ActionRejected("invalid swipe point")
            for coordinate in point:
                _coordinate(coordinate)
        duration = action.get("duration_ms", 300)
        if type(duration) is not int or not (1 <= duration <= 120000):
            raise ActionRejected("invalid swipe duration")
    if name == "text":
        value = _required_string(action, "text", 4096)
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ActionRejected("control characters are not supported by text injection")
    if name == "keyevent" and not KEYEVENT.fullmatch(
        _required_string(action, "key", 40)
    ):
        raise ActionRejected("invalid keyevent")
    if name in MUTATING_ACTIONS:
        for key in AUTH_FIELDS:
            value = _required_string(action, key, 128)
            if key not in {"created_at", "expires_at"} and not IDENTITY.fullmatch(value):
                raise ActionRejected("invalid authorization field: " + key)
        created = _timestamp(action["created_at"])
        expires = _timestamp(action["expires_at"])
        now = datetime.now(timezone.utc)
        if created > now + timedelta(seconds=60):
            raise ActionRejected("authorization not yet valid")
        if not created < expires <= created + timedelta(minutes=5):
            raise ActionRejected("invalid authorization lifetime")
        if expires <= now:
            raise ActionRejected("authorization expired")
    return name


def require_authorization(action: dict, authorizer: Any) -> None:
    """Require a *trusted* governor's identity-bound decision.

    Constructing this dispatcher with an untrusted policy adapter defeats the
    boundary; the CLI deliberately installs none and therefore cannot mutate.
    """
    if authorizer is None or not callable(getattr(authorizer, "authorize", None)):
        raise PolicyBlocked("BLOCKED_BY_POLICY: no trusted governor adapter")
    decision = authorizer.authorize(action)
    if not isinstance(decision, dict) or decision.get("decision") != "ALLOW":
        raise PolicyBlocked("BLOCKED_BY_POLICY: governor denied or escalated")
    if any(decision.get(key) != action.get(key) for key in MATCH_FIELDS):
        raise PolicyBlocked("BLOCKED_BY_POLICY: authorization binding mismatch")
