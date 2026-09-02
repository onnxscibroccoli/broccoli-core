"""Local reminder log. Termux-notification when present. Offline."""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.device import notify

DEFAULT_PATH = Path.home() / ".broccoli" / "reminders.jsonl"

_AT_CLOCK = re.compile(r"\b(?:at|@)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.I)


def reminder_path() -> Path:
    override = os.environ.get("BROCCOLI_REMINDER_PATH", "").strip()
    if override:
        return Path(override)
    return DEFAULT_PATH


def parse_when(text: str) -> Optional[str]:
    raw = (text or "").strip()
    if not raw:
        return None
    m = _AT_CLOCK.search(raw)
    if not m:
        if "tomorrow" in raw.lower():
            return "tomorrow"
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = (m.group(3) or "").lower()
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if hour > 23 or minute > 59:
        return None
    return f"{hour:02d}:{minute:02d}"


class ReminderStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else reminder_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(self, text: str, *, kind: str = "reminder") -> Dict[str, Any]:
        rec = {
            "id": str(int(time.time() * 1000)),
            "ts": time.time(),
            "kind": kind,
            "text": (text or "").strip(),
            "when": parse_when(text or ""),
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, separators=(",", ":")) + "\n")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        label = rec["when"] or "unspecified time"
        notify(f"{rec['text'] or kind} ({label})", title="Broccoli reminder")
        return rec

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        if not self.path.is_file():
            return []
        rows: List[Dict[str, Any]] = []
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        return rows[-limit:]
