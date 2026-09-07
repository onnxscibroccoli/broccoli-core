from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

SENSITIVE_ROLES = frozenset(
    {
        "password",
        "passwd",
        "pin",
        "otp",
        "2fa",
        "token",
        "secret",
        "credential",
        "cvv",
        "ssn",
    }
)
_SENSITIVE_RE = re.compile(
    r"password|passwd|\bpin\b|\botp\b|token|secret|credential|cvv|\bssn\b",
    re.I,
)


def redact_value(role: str, text: str) -> str:
    blob = f"{role} {text}"
    if role.lower() in SENSITIVE_ROLES or _SENSITIVE_RE.search(blob):
        return "[REDACTED]"
    return text


class WatchSession:
    def __init__(self, title: str, requested_by: str = "user") -> None:
        self.id = "watch-" + uuid4().hex[:12]
        self.title = title.strip() or "untitled"
        self.requested_by = requested_by
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.steps: List[Dict[str, Any]] = []
        self._open = True

    def record(
        self,
        action: str,
        role: str = "",
        text: str = "",
        semantic_id: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._open:
            raise RuntimeError("session closed")
        action = action.strip().lower()
        if action not in {
            "tap",
            "focus",
            "input",
            "submit",
            "observe",
            "wait",
            "navigate",
            "back",
        }:
            raise ValueError(f"unknown action: {action}")
        stored = redact_value(role, text)
        step = {
            "n": len(self.steps) + 1,
            "action": action,
            "role": role,
            "semantic_id": semantic_id,
            "text": stored,
            "redacted": stored == "[REDACTED]" and bool(text),
        }
        if extra:
            step["extra"] = {
                k: v for k, v in extra.items() if k.lower() not in SENSITIVE_ROLES
            }
        self.steps.append(step)
        return step

    def ingest_accessibility(self, nodes: List[Dict[str, Any]]) -> int:
        added = 0
        for node in nodes:
            role = str(node.get("role") or node.get("hint") or "")
            sid = str(node.get("semantic_id") or node.get("id") or "")
            text = str(node.get("text") or node.get("content") or "")
            pwd = bool(node.get("password") or node.get("is_password"))
            clicked = bool(node.get("clicked") or node.get("action") == "tap")
            typed = node.get("action") == "input" or bool(node.get("typed"))
            if pwd:
                self.record("focus", role=role or "password", text="", semantic_id=sid)
                added += 1
                continue
            if typed:
                self.record("input", role=role, text=text, semantic_id=sid)
                added += 1
            elif clicked:
                self.record("tap", role=role, text=text, semantic_id=sid)
                added += 1
        return added

    def finish(self, authorize: bool) -> Dict[str, Any]:
        self._open = False
        return {
            "id": self.id,
            "title": self.title,
            "requested_by": self.requested_by,
            "started_at": self.started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "authorized": bool(authorize),
            "steps": list(self.steps),
        }
