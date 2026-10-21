#!/usr/bin/env python3
"""Initialize the local Broccoli vector store.

Creates ~/.broccoli/vectors and an empty index.jsonl (mode 600).
No network. No cloud provider.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.memory.cli import build_stack  # noqa: E402


def main() -> int:
    stack = build_stack()
    stack["root"].mkdir(parents=True, exist_ok=True)
    stack["store"].flush()
    payload = stack["store"].health()
    payload["init"] = "ok"
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
