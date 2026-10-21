#!/usr/bin/env python3
"""Retired legacy Rish/intent launcher: delegate to the canonical core wrapper."""
import subprocess
import sys
from pathlib import Path

WRAPPER = Path(__file__).resolve().parents[1] / "lib/rish_run.sh"

def rish_exec(command_line: str):
    return subprocess.run(["bash", str(WRAPPER), command_line], capture_output=True, text=True, timeout=600)

if __name__ == "__main__":
    result = rish_exec(" ".join(sys.argv[1:]))
    print((result.stdout or "") + (result.stderr or ""), end="")
    sys.exit(result.returncode)
