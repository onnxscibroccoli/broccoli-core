"""Feed accessibility observer events into an open WatchSession."""
from __future__ import annotations

from typing import Any, Dict, Iterable

from runtime.watchme.record import WatchSession


class WatchBridge:
    def __init__(self, session: WatchSession) -> None:
        self.session = session
        self.accepted = 0

    def on_event(self, ev: Dict[str, Any]) -> None:
        et = str(ev.get("event_type") or ev.get("type") or "")
        payload = ev.get("payload") or {}
        sid = str(ev.get("stable_id") or payload.get("stable_id") or "")
        role = str(payload.get("class_name") or payload.get("role") or "")
        text = str(payload.get("text") or payload.get("content_desc") or "")
        pwd = bool(payload.get("password") or payload.get("is_password"))
        if pwd:
            self.session.record("focus", role=role or "password", text="", semantic_id=sid)
            self.accepted += 1
            return
        if et in ("FOCUS_CHANGED", "focus"):
            self.session.record("focus", role=role, text=text, semantic_id=sid)
            self.accepted += 1
        elif et in ("NODE_ADDED", "NODE_UPDATED", "CONTENT_CHANGED", "UI_CHANGED"):
            if payload.get("clickable") or payload.get("clicked"):
                self.session.record("tap", role=role, text=text, semantic_id=sid)
                self.accepted += 1
            elif payload.get("typed") or payload.get("action") == "input":
                self.session.record("input", role=role, text=text, semantic_id=sid)
                self.accepted += 1
            else:
                self.session.record("observe", role=role, text=text, semantic_id=sid)
                self.accepted += 1

    def drain(self, events: Iterable[Any]) -> int:
        n = 0
        for ev in events:
            if hasattr(ev, "to_dict"):
                self.on_event(ev.to_dict())
            elif isinstance(ev, dict):
                self.on_event(ev)
            n += 1
        return n
