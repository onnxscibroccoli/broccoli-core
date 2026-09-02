"""Offline provider. No network, no commercial gate, no token.

Used for tests, degraded mode, and proving the stack is provider-agnostic.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from runtime.providers.base import Provider


class EchoProvider(Provider):
    def __init__(self, bus=None) -> None:
        self.bus = bus
        self.session_active = False
        self._last = None

    def initialize(self) -> bool:
        self.session_active = True
        if self.bus:
            self.bus.publish("ProviderConnected", {"provider": "echo"}, source="EchoProvider")
        return True

    def send(self, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if not self.session_active:
            self.initialize()
        self._last = message
        payload = {"provider": "echo", "request": message, "response": f"echo: {message}"}
        if self.bus:
            self.bus.publish("ProviderResult", payload, source="EchoProvider")
        return True

    def stream(self, message: str, context: Optional[Dict[str, Any]] = None):
        return self.send(message, context)

    def health(self) -> Dict[str, Any]:
        return {"status": "healthy", "provider": "echo", "session": self.session_active, "commercial": False}

    def shutdown(self) -> bool:
        self.session_active = False
        if self.bus:
            self.bus.publish("ProviderDisconnected", "echo", source="EchoProvider")
        return True

    def capabilities(self) -> Dict[str, bool]:
        return {"chat": True, "vision": False, "tools": False, "streaming": False, "offline": True}
