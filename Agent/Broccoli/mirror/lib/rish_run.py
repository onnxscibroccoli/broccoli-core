#!/usr/bin/env python3
"""Run Termux commands via RISH intent when available; else local shell."""
import json, os, subprocess, sys
from pathlib import Path

HOME = Path.home()
RISH = HOME / ".termux" / "tasker" / "rish"  # common
RISH2 = HOME / "bin" / "rish"

def has_rish():
    for p in (RISH, RISH2, Path("/data/data/com.termux/files/usr/bin/rish")):
        if p.exists():
            return str(p)
    which = subprocess.run(["which", "rish"], capture_output=True, text=True)
    return which.stdout.strip() if which.returncode == 0 else None

def local_shell(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, cwd=cwd or str(HOME), capture_output=True, text=True, timeout=600)

def rish_exec(command_line: str):
    """Fire com.termux.RUN_COMMAND through am (same as Tasker/RISH)."""
    rish = has_rish()
    if rish:
        return subprocess.run([rish, command_line], capture_output=True, text=True, timeout=600)
    # am broadcast fallback
    payload = json.dumps({
        "com.termux.RUN_COMMAND_PATH": "/data/data/com.termux/files/usr/bin/bash",
        "com.termux.RUN_COMMAND_ARGUMENTS": ["-lc", command_line],
        "com.termux.RUN_COMMAND_WORKDIR": str(HOME),
        "com.termux.RUN_COMMAND_BACKGROUND": False,
    })
    return subprocess.run([
        "am", "broadcast", "--user", "0",
        "-a", "com.termux.RUN_COMMAND",
        "--es", "com.termux.RUN_COMMAND", payload,
    ], capture_output=True, text=True, timeout=30)

if __name__ == "__main__":
    cmd = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "echo rish_ok"
    r = rish_exec(cmd)
    print(r.stdout or r.stderr or "", end="")
    sys.exit(r.returncode)
