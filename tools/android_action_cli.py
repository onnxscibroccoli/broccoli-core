"""CLI boundary for bounded Android agent actions.

Input: one JSON object on stdin.
Output: one JSON object on stdout.
No arbitrary shell command is accepted.
"""

from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.actions import ActionDispatcher
from tools.android_transport import RishTransport
from tools.android_action_policy import PolicyBlocked

MAX_ACTION_BYTES = 16384


def no_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate action JSON key")
        result[key] = value
    return result


def reject_non_json_number(value):
    raise ValueError("invalid JSON numeric constant")




def main() -> int:
    try:
        raw = sys.stdin.read(MAX_ACTION_BYTES + 1)
        if len(raw.encode("utf-8")) > MAX_ACTION_BYTES:
            raise ValueError("action payload exceeds size limit")
        action = json.loads(
            raw,
            object_pairs_hook=no_duplicate_pairs,
            parse_constant=reject_non_json_number,
        )
        if not isinstance(action, dict):
            raise ValueError("action must be a JSON object")
        result = ActionDispatcher(RishTransport()).execute(action)
        if hasattr(result, "returncode"):
            payload = {
                "ok": result.ok,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "combined_output": result.combined_output,
                "action": action.get("action"),
            }
        else:
            payload = {"ok": True, "result": result}
        print(json.dumps(payload, sort_keys=True))
        return 0 if payload.get("ok") else 1
    except PolicyBlocked:
        print(json.dumps({
            "ok": False,
            "status": "BLOCKED_BY_POLICY",
            "error": "PolicyBlocked",
        }, sort_keys=True))
        return 2
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "error": "ValueError" if isinstance(exc, ValueError) else type(exc).__name__,
            "message": str(exc),
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
