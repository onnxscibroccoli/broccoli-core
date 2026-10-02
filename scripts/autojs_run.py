#!/usr/bin/env python3
"""Optional AutoJS adapter for Broccoli Android automation.

All Android activity launches go through the canonical Rish transport so this
works both from an interactive Termux shell and from reduced RDC/background
processes that must re-enter Termux through RunCommandService.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import shlex
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.android_transport import RishTransport

SD = Path(os.environ.get("BROCC_AUTOJS_DIR", "/sdcard/broccoli/autojs"))
UI = Path(os.environ.get("BROCC_UI_DIR", "/sdcard/broccoli/ui"))
PKG = os.environ.get("AUTOJS_PKG", "org.autojs.autojs.modify")
ACT = os.environ.get(
    "AUTOJS_ACT", "org.autojs.autojs.external.open.RunIntentActivity"
)


class AutoJSError(RuntimeError):
    pass


def _launch(path: Path, timeout: float = 15.0):
    component = f"{PKG}/{ACT}"
    uri = f"file://{path}"
    command = (
        f"am start -W -n {shlex.quote(component)} "
        f"-d {shlex.quote(uri)}"
    )
    result = RishTransport(timeout=timeout).run(command, timeout=timeout)
    if not result.ok:
        detail = result.combined_output.strip().replace("\n", " ")
        raise AutoJSError(
            f"AutoJS launch failed rc={result.returncode}: {detail[:500]}"
        )
    return result


def run_js(name: str, wait_out: str | Path | None = None, timeout: float = 20.0) -> bool:
    path = SD / name
    if not path.is_file():
        raise FileNotFoundError(path)

    output = Path(wait_out) if wait_out else None
    before_mtime = None
    if output and output.exists():
        before_mtime = output.stat().st_mtime_ns

    _launch(path)
    if output is None:
        return True

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if output.is_file():
            current_mtime = output.stat().st_mtime_ns
            if before_mtime is None or current_mtime > before_mtime:
                return True
        time.sleep(0.25)
    return False


def smoke(timeout: float = 8.0) -> str:
    SD.mkdir(parents=True, exist_ok=True)
    UI.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(8)
    script = SD / f"_broccoli_smoke_{token}.js"
    marker = UI / f"autojs_smoke_{token}.txt"
    expected = f"BROCCOLI_AUTOJS_OK {token} "
    marker_js = json.dumps(str(marker))
    expected_js = json.dumps(expected)
    script.write_text(
        f"files.write({marker_js}, {expected_js} + new Date().toISOString());\nexit();\n",
        encoding="utf-8",
    )
    try:
        if not run_js(script.name, marker, timeout=timeout):
            raise AutoJSError(f"AutoJS smoke output timed out: {marker}")
        value = marker.read_text(encoding="utf-8", errors="replace").strip()
        if not value.startswith(expected):
            raise AutoJSError(f"Unexpected AutoJS smoke marker: {value!r}")
        return value
    finally:
        script.unlink(missing_ok=True)
        marker.unlink(missing_ok=True)


def _print_output(path: Path, *, tail: int | None = None) -> None:
    data = path.read_text(encoding="utf-8", errors="replace")
    print(data[-tail:] if tail else data)


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "smoke"
    try:
        if cmd == "smoke":
            print("autojs_smoke_ok", smoke())
            return 0
        if cmd == "fsm":
            out = UI / "button_state.json"
            if not run_js("grok_button_fsm.js", out, timeout=25):
                raise AutoJSError(f"AutoJS output timed out: {out}")
            _print_output(out)
            return 0
        if cmd == "read":
            out = UI / "last_capture.txt"
            if not run_js("grok_read_chat.js", out, timeout=20):
                raise AutoJSError(f"AutoJS output timed out: {out}")
            _print_output(out, tail=500)
            return 0
        print(f"usage: {argv[0]} [smoke|read|fsm]", file=sys.stderr)
        return 64
    except FileNotFoundError as exc:
        print(f"AUTOJS_PAYLOAD_MISSING: {exc.filename or exc}", file=sys.stderr)
        return 2
    except (AutoJSError, TimeoutError) as exc:
        print(f"AUTOJS_ERROR: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
