from __future__ import annotations

import time
from typing import Any, Dict, Optional


class GrokAgent:
    """Thin agent wrapper around the Grok provider.

    Registered with AgentCoordinator and exposed as a managed transport so the
    Governor can restart it when it goes stale.
    """

    def __init__(self, provider=None, bus=None):
        self.provider = provider
        self.bus = bus
        self._running = False
        self._tasks_executed = 0
        self._last_error: Optional[str] = None
        self._started_at: Optional[float] = None

    def start(self):
        if self._running:
            return self
        if self.provider is not None and hasattr(self.provider, "initialize"):
            try:
                self.provider.initialize()
            except Exception as exc:  # pragma: no cover - defensive
                self._last_error = str(exc)
        self._running = True
        self._started_at = time.time()
        return self

    def stop(self):
        if not self._running:
            return self
        if self.provider is not None and hasattr(self.provider, "shutdown"):
            try:
                self.provider.shutdown()
            except Exception:
                pass
        self._running = False
        return self

    def health(self) -> Dict[str, Any]:
        provider_health = {}
        if self.provider is not None and hasattr(self.provider, "health"):
            try:
                provider_health = self.provider.health() or {}
            except Exception as exc:
                provider_health = {"status": "error", "error": str(exc)}
        return {
            "running": self._running,
            "tasks_executed": self._tasks_executed,
            "last_error": self._last_error,
            "started_at": self._started_at,
            "provider": provider_health,
        }

    def execute(self, task):
        if not self._running:
            # Auto-start so a cold agent still does work instead of silently no-op.
            self.start()
        self._tasks_executed += 1
        if self.provider is not None and hasattr(self.provider, "send"):
            try:
                message = getattr(task, "description", None) or str(task)
                self.provider.send(message, context={"task_id": getattr(task, "id", None)})
            except Exception as exc:
                self._last_error = str(exc)
                if self.bus is not None:
                    try:
                        self.bus.publish(
                            "AgentExecutionFailed",
                            {"agent": "grok", "task": task, "error": str(exc)},
                            source="GrokAgent",
                        )
                    except Exception:
                        pass
                return False
        if self.bus is not None:
            try:
                self.bus.publish(
                    "AgentExecuted",
                    {"agent": "grok", "task": task},
                    source="GrokAgent",
                )
            except Exception:
                pass
        return True
