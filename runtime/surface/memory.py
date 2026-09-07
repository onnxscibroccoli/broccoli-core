"""In-memory VirtualSurface.

Runs in CI and Termux without rish, AccessibilityService, or a
provider app. Failures are explicit events, never swallowed.
"""
from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

from runtime.surface.protocol import SurfaceEvent, SurfaceState


class MemorySurface:
    def __init__(self, session: str = "ready") -> None:
        if session not in (
            "unknown",
            "ready",
            "unauthenticated",
            "unavailable",
            "stale",
            "failed",
        ):
            session = "unknown"
        self._session = session
        self._id = "surf-" + uuid4().hex[:12]
        self._attached = False
        self._focused = False
        self._destroyed = False
        self._buffer = ""
        self._submitted: List[str] = []
        self._provider_id = ""
        self._events: List[SurfaceEvent] = []

    def _emit(self, ok: bool, op: str, code: str = "ok", message: str = "", **details) -> SurfaceEvent:
        ev = SurfaceEvent(
            ok=ok,
            op=op,
            state=self._session if not self._destroyed else "failed",
            code=code,
            message=message,
            details=details,
        )
        self._events.append(ev)
        return ev

    def _guard(self, op: str) -> Optional[SurfaceEvent]:
        if self._destroyed:
            return self._emit(False, op, "destroyed", "surface destroyed")
        if self._session == "unavailable":
            return self._emit(False, op, "unavailable", "provider or display unavailable")
        return None

    def create(self, provider_id: str = "") -> SurfaceEvent:
        blocked = self._guard("create")
        if blocked:
            return blocked
        self._provider_id = provider_id
        self._attached = True
        return self._emit(True, "create", surface_id=self._id, provider_id=provider_id)

    def attach(self) -> SurfaceEvent:
        blocked = self._guard("attach")
        if blocked:
            return blocked
        self._attached = True
        return self._emit(True, "attach", surface_id=self._id)

    def inspect(self) -> SurfaceState:
        return SurfaceState(
            surface_id=self._id,
            attached=self._attached and not self._destroyed,
            focused=self._focused and not self._destroyed,
            session=self._session if not self._destroyed else "failed",
            provider_id=self._provider_id,
            notes=list(self._submitted[-3:]),
        )

    def focus(self) -> SurfaceEvent:
        blocked = self._guard("focus")
        if blocked:
            return blocked
        if not self._attached:
            return self._emit(False, "focus", "not_attached", "attach before focus")
        self._focused = True
        return self._emit(True, "focus")

    def input(self, text: str) -> SurfaceEvent:
        blocked = self._guard("input")
        if blocked:
            return blocked
        if self._session == "unauthenticated":
            return self._emit(
                False,
                "input",
                "unauthenticated",
                "session requires provider authenticate capability; core will not type credentials",
            )
        if not self._focused:
            return self._emit(False, "input", "not_focused", "focus before input")
        self._buffer = text
        return self._emit(True, "input", chars=len(text))

    def submit(self) -> SurfaceEvent:
        blocked = self._guard("submit")
        if blocked:
            return blocked
        if self._session == "unauthenticated":
            return self._emit(False, "submit", "unauthenticated", "session not ready")
        if not self._focused:
            return self._emit(False, "submit", "not_focused", "focus before submit")
        self._submitted.append(self._buffer)
        self._buffer = ""
        return self._emit(True, "submit", count=len(self._submitted))

    def observe(self) -> SurfaceEvent:
        blocked = self._guard("observe")
        if blocked:
            return blocked
        return self._emit(
            True,
            "observe",
            attached=self._attached,
            focused=self._focused,
            session=self._session,
            pending=len(self._buffer),
            submitted=len(self._submitted),
        )

    def recover(self) -> SurfaceEvent:
        if self._destroyed:
            return self._emit(False, "recover", "destroyed", "cannot recover destroyed surface")
        if self._session == "unauthenticated":
            return self._emit(
                False,
                "recover",
                "unauthenticated",
                "governor should request provider session.authenticate; core does not log in",
            )
        if self._session in ("stale", "failed"):
            self._session = "ready"
            self._attached = True
            self._focused = False
            return self._emit(True, "recover", session=self._session)
        self._attached = True
        return self._emit(True, "recover", session=self._session)

    def detach(self) -> SurfaceEvent:
        self._attached = False
        self._focused = False
        return self._emit(True, "detach")

    def destroy(self) -> SurfaceEvent:
        self._destroyed = True
        self._attached = False
        self._focused = False
        return self._emit(True, "destroy")
