#!/usr/bin/env python3
"""Loop execution pulse — non-blocking heartbeat."""
import json
import sys
import time
from pathlib import Path

ROOT = Path("/data/data/com.termux/files/home/broccoli")
LOG = ROOT / "logs" / "pulse.log"

def tick(interval: float = 1.0, count: int = 3) -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        line = {"ts": time.time(), "i": i, "status": "ok"}
        with LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        time.sleep(interval)
    return 0

def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv:
        return tick()
    if argv[0] == "once":
        return tick(count=1)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
