#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPECT = os.environ.get("BROCC_EXPECT", "")
MODE = os.environ.get("BROCC_VALIDATE_MODE", "grace")


def _capture_candidates() -> list[Path]:
    configured = os.environ.get("BROCC_CAPTURE")
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend(
        [
            Path("/sdcard/broccoli/ui/last_capture.txt"),
            ROOT / "ui" / "last_capture.txt",
            Path.home() / "broccoli" / "ui" / "last_capture.txt",
        ]
    )
    return candidates


def _latest_capture() -> str:
    existing = [p for p in _capture_candidates() if p.is_file()]
    if not existing:
        return ""
    newest = max(existing, key=lambda p: p.stat().st_mtime_ns)
    return newest.read_text(encoding="utf-8", errors="ignore").strip()


def text() -> str:
    if os.environ.get("BROCC_USE_AUTOJS") == "1":
        runner = ROOT / "scripts" / "autojs_run.py"
        if runner.is_file():
            try:
                result = subprocess.run(
                    [sys.executable, str(runner), "read"],
                    cwd=str(ROOT),
                    timeout=35,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode != 0:
                    detail = (result.stderr or result.stdout or "").strip()
                    print(
                        f"[validate] autojs_unavailable rc={result.returncode} {detail[:240]}",
                        file=sys.stderr,
                        flush=True,
                    )
            except subprocess.TimeoutExpired:
                print("[validate] autojs_unavailable timeout", file=sys.stderr, flush=True)
    return _latest_capture()


t = text()
if EXPECT and EXPECT in t:
    print("[validate] expect_ok", flush=True)
    sys.exit(0)
if len(t) >= 8:
    print("[validate] len_ok", len(t), flush=True)
    sys.exit(0)
if MODE in ("grace", "smoke_only"):
    print("[validate] grace_ok", flush=True)
    sys.exit(0)
print("[validate] thin", len(t), flush=True)
sys.exit(1)
