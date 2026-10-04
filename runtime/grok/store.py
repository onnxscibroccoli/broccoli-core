"""Persistent investigation records. Phase 1 writes status snapshots only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def status_dir(root: Path) -> Path:
    path = root / "data" / "grok" / "status"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_status(root: Path, envelope: Dict[str, Any]) -> Path:
    stamp = str(envelope.get("timestamp", "unknown")).replace(":", "")
    cid = envelope.get("correlation_id", "nocid")
    path = status_dir(root) / f"{stamp}_{cid}.json"
    path.write_text(json.dumps(envelope, indent=2, default=str) + "\n", encoding="utf-8")
    latest = root / "data" / "grok" / "status-latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return path
