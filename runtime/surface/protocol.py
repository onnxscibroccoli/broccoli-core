"""Uniform virtual-display / background execution surface.

Lifecycle verbs Core may call without knowing the provider:

    create/attach, inspect, focus, input, submit, observe, recover, detach

Auth is an observable session state. Core never fills credentials.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol


ALLOWED_OPS = (
    "create",
    "attach",
    "inspect",
    "focus",
    "input",
    "submit",
    "observe",
    "recover",
    "detach",
    "destroy",
)

SESSION_STATES = (
    "unknown",
    "ready",
    "unauthenticated",
    "unavailable",
    "stale",
    "failed",
)


class SurfaceError(Exception):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def as_event(self, op: str) -> "SurfaceEvent":
        return SurfaceEvent(
            ok=False,
            op=op,
            state="failed",
            code=self.code,
            message=self.message,
            details=dict(self.details),
        )


@dataclass
class SurfaceState:
    surface_id: str
    attached: bool = False
    focused: bool = False
    session: str = "unknown"
    provider_id: str = ""
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "surface_id": self.surface_id,
            "attached": self.attached,
            "focused": self.focused,
            "session": self.session,
            "provider_id": self.provider_id,
            "notes": list(self.notes),
        }


@dataclass
class SurfaceEvent:
    ok: bool
    op: str
    state: str
    code: str = "ok"
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "op": self.op,
            "state": self.state,
            "code": self.code,
            "message": self.message,
            "details": dict(self.details),
        }


class VirtualSurface(Protocol):
    def create(self, provider_id: str = "") -> SurfaceEvent: ...
    def attach(self) -> SurfaceEvent: ...
    def inspect(self) -> SurfaceState: ...
    def focus(self) -> SurfaceEvent: ...
    def input(self, text: str) -> SurfaceEvent: ...
    def submit(self) -> SurfaceEvent: ...
    def observe(self) -> SurfaceEvent: ...
    def recover(self) -> SurfaceEvent: ...
    def detach(self) -> SurfaceEvent: ...
    def destroy(self) -> SurfaceEvent: ...
