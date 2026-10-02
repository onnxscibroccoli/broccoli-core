"""Bounded RDC/background bridge into Termux RunCommandService.

This is deliberately not a second Android transport. It only moves a command
into the canonical Termux context, where lib/rish_run.sh remains authoritative.
"""
from __future__ import annotations

import base64
import os
from pathlib import Path
import secrets
import subprocess
import time

PREFIX = "/data/data/com.termux/files"
AM = "/system/bin/am"
BASH = f"{PREFIX}/usr/bin/bash"
BRIDGE_DIR = Path("/sdcard/OmniKali/broccoli/rdc-run-command")


def available() -> bool:
    return os.path.isfile(AM) and os.path.isfile(BASH)


def _script(command: str, tmp: str, out: str) -> str:
    encoded = base64.b64encode(command.encode()).decode()
    qtmp = repr(tmp)
    qout = repr(out)
    return (
        f"printf '%s' {encoded} | base64 -d | bash > {qtmp} 2>&1; "
        f"rc=$?; printf '\\n__OMNIKALI_RC__=%s\\n' \"$rc\" >> {qtmp}; "
        f"mv {qtmp} {qout}"
    )


def run(command: str, timeout: float = 30.0):
    if not isinstance(command, str) or not command.strip():
        raise ValueError("command must be a non-empty string")
    if not available():
        raise RuntimeError("TERMUX_RUN_COMMAND_UNAVAILABLE")

    token = secrets.token_hex(12)
    out = BRIDGE_DIR / f"{token}.out"
    tmp = BRIDGE_DIR / f".{token}.tmp"
    subprocess.run(["/system/bin/mkdir", "-p", str(BRIDGE_DIR)], check=True)

    script = _script(command, str(tmp), str(out))
    args = ["-lc," + script]
    subprocess.run(
        [
            AM,
            "startservice", "--user", "0",
            "-n", "com.termux/com.termux.app.RunCommandService",
            "-a", "com.termux.RUN_COMMAND",
            "--es", "com.termux.RUN_COMMAND_PATH", BASH,
            "--esa", "com.termux.RUN_COMMAND_ARGUMENTS", args[0],
            "--es", "com.termux.RUN_COMMAND_WORKDIR", "/data/data/com.termux/files/home",
            "--ez", "com.termux.RUN_COMMAND_BACKGROUND", "true",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    deadline = time.monotonic() + float(timeout)
    while time.monotonic() < deadline:
        try:
            data = Path(out).read_text()
        except FileNotFoundError:
            time.sleep(0.1)
            continue
        marker = "__OMNIKALI_RC__="
        if marker not in data:
            time.sleep(0.1)
            continue
        body, rc_text = data.rsplit(marker, 1)
        rc = int(rc_text.strip().splitlines()[0])
        try:
            Path(out).unlink()
        except FileNotFoundError:
            pass
        try:
            Path(tmp).unlink()
        except FileNotFoundError:
            pass
        return rc, body, ""

    raise TimeoutError(f"Termux RunCommand timed out after {timeout:.1f}s")
