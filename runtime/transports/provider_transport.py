from __future__ import annotations

from typing import Any, Optional


class ProviderTransport:
    """
    Adapter that exposes a provider object as a transport.

    It is intentionally duck-typed:
    - start() calls initialize() if present
    - stop() calls shutdown()/close()/stop() if present
    - health() merges provider.health() if present
    """

    def __init__(self, name: str, provider: Any):
        self.name = name
        self.provider = provider
        self._running = False
        self._last_error: Optional[str] = None

    def start(self):
        if hasattr(self.provider, "initialize"):
            self.provider.initialize()
        self._running = True
        self._last_error = None
        return self

    def stop(self):
        for method_name in ("shutdown", "close", "stop"):
            method = getattr(self.provider, method_name, None)
            if callable(method):
                try:
                    method()
                except Exception as exc:
                    self._last_error = str(exc)
                break
        self._running = False
        return self

    def health(self):
        payload = {}
        if hasattr(self.provider, "health"):
            try:
                payload = self.provider.health() or {}
            except Exception as exc:
                self._last_error = str(exc)
                payload = {}

        return {
            "running": self._running,
            "last_error": self._last_error,
            **payload,
        }
