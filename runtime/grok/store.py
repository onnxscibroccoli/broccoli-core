"""Persistent evidence envelopes. Broccoli is the system of record."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def status_dir(root: Path) -> Path:
    path = root / "data" / "grok" / "status"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_status(root: Path, envelope: dict[str, Any]) -> Path:
    directory = status_dir(root)
    stamp = str(envelope.get("collected_at") or "unknown").replace(":", "")
    correlation = str(envelope.get("correlation_id") or "status")
    path = directory / f"{stamp}_{correlation}.json"
    path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    latest = directory / "latest.json"
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path
