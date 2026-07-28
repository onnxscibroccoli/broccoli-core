"""Normalized semantic accessibility events."""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Optional
import time
import uuid


class SemanticEventType(str, Enum):
    NODE_ADDED = "NODE_ADDED"
    NODE_UPDATED = "NODE_UPDATED"
    NODE_REMOVED = "NODE_REMOVED"
    WINDOW_CHANGED = "WINDOW_CHANGED"
    FOCUS_CHANGED = "FOCUS_CHANGED"
    CONTENT_CHANGED = "CONTENT_CHANGED"
    SCROLL_CHANGED = "SCROLL_CHANGED"
    SCREEN_CHANGED = "SCREEN_CHANGED"
    UI_CHANGED = "UI_CHANGED"  # aggregate / catch-all


@dataclass
class SemanticEvent:
    event_type: SemanticEventType
    timestamp: float = field(default_factory=time.time)
    package: str = ""
    window_id: int = -1
    stable_id: str = ""          # durable semantic identity of the node
    confidence: float = 1.0
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SemanticEvent":
        et = data.get("event_type", "UI_CHANGED")
        if isinstance(et, str):
            et = SemanticEventType(et)
        return cls(
            event_type=et,
            timestamp=float(data.get("timestamp", time.time())),
            package=str(data.get("package", "")),
            window_id=int(data.get("window_id", -1)),
            stable_id=str(data.get("stable_id", "")),
            confidence=float(data.get("confidence", 1.0)),
            payload=dict(data.get("payload") or {}),
            event_id=str(data.get("event_id") or uuid.uuid4().hex[:12]),
        )


def make_event(
    event_type: SemanticEventType,
    *,
    package: str = "",
    window_id: int = -1,
    stable_id: str = "",
    confidence: float = 1.0,
    **payload,
) -> SemanticEvent:
    return SemanticEvent(
        event_type=event_type,
        package=package,
        window_id=window_id,
        stable_id=stable_id,
        confidence=max(0.0, min(1.0, confidence)),
        payload=payload,
    )
