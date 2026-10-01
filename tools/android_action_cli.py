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


def main() -> int:
    try:
        action = json.load(sys.stdin)
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
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "error": type(exc).__name__,
            "message": str(exc),
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
