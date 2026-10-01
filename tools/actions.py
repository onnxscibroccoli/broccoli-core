"""Allowlisted Android action contract for agentic local orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import shlex
from typing import Any

from tools.android_transport import RishTransport, TransportResult


Actions = dict[str, Any]


@dataclass
class ActionDispatcher:
    backend: Any

    ALLOWED = frozenset({
        "device.identity",
        "display.list",
        "tap",
        "swipe",
        "text",
        "keyevent",
    })

    def execute(self, action: Actions) -> Any:
        name = action.get("action")
        if name not in self.ALLOWED:
            raise ValueError(f"Unknown or disallowed action: {name!r}")

        if name == "device.identity":
            return self.backend.run(
                "echo OMNIKALI_ANDROID_IDENTITY_OK; id; "
                "echo sdk=$(getprop ro.build.version.sdk); "
                "echo device=$(getprop ro.product.device)"
            )

        if name == "display.list":
            return self.backend.run(
                "dumpsys display | grep -E 'mDisplayId=[0-9]+'"
            )

        if name == "tap":
            return self.backend.run(
                f"input -d {int(action['display_id'])} tap "
                f"{int(action['x'])} {int(action['y'])}"
            )

        if name == "swipe":
            start = action["start"]
            end = action["end"]
            duration = int(action.get("duration_ms", 300))
            if duration < 1 or duration > 120000:
                raise ValueError("duration_ms must be between 1 and 120000")
            return self.backend.run(
                f"input -d {int(action['display_id'])} swipe "
                f"{int(start[0])} {int(start[1])} "
                f"{int(end[0])} {int(end[1])} {duration}"
            )

        if name == "text":
            value = str(action["text"])
            if len(value) > 4096:
                raise ValueError("text exceeds 4096 character action limit")
            # Android input text uses %s for spaces. Shell-quote the value.
            encoded = value.replace("%", "%25").replace(" ", "%s")
            return self.backend.run(
                f"input -d {int(action['display_id'])} text "
                f"{shlex.quote(encoded)}"
            )

        if name == "keyevent":
            key = str(action["key"])
            if not key or len(key) > 40 or not all(
                c.isalnum() or c in "_-" for c in key
            ):
                raise ValueError("invalid keyevent")
            return self.backend.run(
                f"input -d {int(action['display_id'])} keyevent {shlex.quote(key)}"
            )

        raise AssertionError("unreachable")
