#!/usr/bin/env python3
"""Report runner — subprocess with timeout; notifications via Popen (non-blocking)."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/data/data/com.termux/files/home/broccoli")
LOG = ROOT / "logs" / "report.log"

def notify(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")
    # Non-blocking: fire-and-forget termux-notification if available
    try:
        subprocess.Popen(
            ["termux-notification", "--title", "Broccoli", "--content", msg[:200]],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass

def run_check(cmd: list[str], timeout: float = 30.0) -> dict:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": p.returncode == 0,
            "code": p.returncode,
            "stdout": (p.stdout or "")[-500:],
            "stderr": (p.stderr or "")[-500:],
        }
    except subprocess.TimeoutExpired:
        notify("report: subprocess timeout")
        return {"ok": False, "code": -1, "stdout": "", "stderr": "timeout"}

def main(argv=None):
    argv = argv or sys.argv[1:]
    notify("report: start")
    result = run_check([sys.executable, str(ROOT / "scripts" / "path_validate.sh")])
    notify("report: " + ("PASS" if result["ok"] else "FAIL"))
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
