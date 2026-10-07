"""Compatibility helpers for Broccoli's Shizuku/Rish Android shell path.

New callers should prefer tools.android_transport.RishTransport directly. This
module delegates to that transport when it is available so legacy callers keep
the same `(returncode, output)` contract without bypassing the RDC-safe bridge.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def rish_path():
    for candidate in (
        os.environ.get("BROCCOLI_RISH"),
        Path(os.environ.get("PREFIX", "")) / "bin/rish",
        Path.home() / "rish",
    ):
        if candidate and Path(str(candidate)).is_file():
            return str(candidate)
    return shutil.which("rish")


def _transport_class():
    """Return the canonical transport class when this checkout contains it."""
    if not (ROOT / "tools" / "android_transport.py").is_file():
        return None
    root = str(ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    try:
        from tools.android_transport import RishTransport
    except ImportError:
        return None
    return RishTransport


def shell(cmd, timeout=45):
    transport = _transport_class()
    if transport is not None:
        result = transport(timeout=timeout).run(cmd, timeout=timeout)
        return result.returncode, result.combined_output

    # Missing canonical transport is an error, never permission to run locally.
    return 78, "RISH_TRANSPORT_MISSING: restore broccoli-core/tools/android_transport.py"


def wm_size():
    _rc, out = shell("wm size")
    match = re.search(r"(\d+)x(\d+)", out)
    return (int(match.group(1)), int(match.group(2))) if match else (1080, 2400)


def rish_ok(timeout=8):
    """Return `(ok, evidence)` for a verified Android shell response."""
    try:
        rc, out = shell(
            "echo BROCCOLI_RISH_OK; id; getprop ro.build.version.sdk",
            timeout=timeout,
        )
        evidence = (out or "").strip()[:400]
        ok = (
            rc == 0
            and "BROCCOLI_RISH_OK" in evidence
            and "uid=2000(shell)" in evidence
        )
        return ok, evidence
    except Exception as exc:
        return False, str(exc)[:400]
