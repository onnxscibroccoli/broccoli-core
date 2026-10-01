"""Allowlisted Android action contract for agentic local orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import re
import shlex
from typing import Any

from tools.android_transport import RishTransport, TransportResult


Actions = dict[str, Any]
PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")


@dataclass
class ActionDispatcher:
    backend: Any

    ALLOWED = frozenset({
        "device.identity",
        "display.list",
        "ui.dump",
        "package.inspect",
        "package.export",
        "app.launch",
        "app.stop",
        "tap",
        "swipe",
        "text",
        "keyevent",
    })

    def _package(self, action: Actions) -> str:
        package = str(action.get("package", ""))
        if not PACKAGE_RE.fullmatch(package):
            raise ValueError("invalid Android package name")
        return package

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

        if name == "ui.dump":
            return self.backend.run(
                "uiautomator dump /data/local/tmp/omnikali-ui.xml >/dev/null 2>&1 "
                "&& cat /data/local/tmp/omnikali-ui.xml"
            )

        if name == "package.inspect":
            package = self._package(action)
            quoted = shlex.quote(package)
            return self.backend.run(
                f"echo OMNIKALI_PACKAGE_INSPECT_OK; "
                f"echo package={quoted}; "
                f"pm path {quoted}; "
                f"dumpsys package {quoted} | grep -E 'versionName=|versionCode=|targetSdk=|firstInstallTime=|lastUpdateTime='"
            )

        if name == "package.export":
            package = self._package(action)
            quoted = shlex.quote(package)
            return self.backend.run(
                f"apk=$(pm path {quoted} | sed -n '1s/^package://p'); "
                "test -n \"$apk\"; "
                "mkdir -p /sdcard/Download/OmniKali/apk; "
                f"out=/sdcard/Download/OmniKali/apk/{package}.apk; "
                "cp \"$apk\" \"$out\"; "
                "sha256sum \"$out\"; "
                "echo OMNIKALI_PACKAGE_EXPORT_OK; "
                "echo path=$out"
            )

        if name == "app.launch":
            package = self._package(action)
            quoted = shlex.quote(package)
            return self.backend.run(
                f"monkey -p {quoted} -c android.intent.category.LAUNCHER 1"
            )

        if name == "app.stop":
            package = self._package(action)
            quoted = shlex.quote(package)
            if action.get("confirm") is not True:
                raise ValueError("app.stop requires confirm=true")
            return self.backend.run(f"am force-stop {quoted}")

        if name == "tap":
            self._display(action)
            return self.backend.run(
                f"input -d {int(action['display_id'])} tap "
                f"{int(action['x'])} {int(action['y'])}"
            )

        if name == "swipe":
            self._display(action)
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
            self._display(action)
            value = str(action["text"])
            if len(value) > 4096:
                raise ValueError("text exceeds 4096 character action limit")
            encoded = value.replace("%", "%25").replace(" ", "%s")
            return self.backend.run(
                f"input -d {int(action['display_id'])} text "
                f"{shlex.quote(encoded)}"
            )

        if name == "keyevent":
            self._display(action)
            key = str(action["key"])
            if not key or len(key) > 40 or not all(
                c.isalnum() or c in "_-" for c in key
            ):
                raise ValueError("invalid keyevent")
            return self.backend.run(
                f"input -d {int(action['display_id'])} keyevent {shlex.quote(key)}"
            )

        raise AssertionError("unreachable")

    @staticmethod
    def _display(action: Actions) -> None:
        display_id = int(action["display_id"])
        if display_id < 0 or display_id > 99:
            raise ValueError("display_id must be between 0 and 99")
