"""Onyx runtime: provider-agnostic, event-driven, autonomous.

Onyx is the thin orchestration layer over ProviderManager. It does not
know about Grok, xAI, or any commercial ledger. Providers register
themselves; Onyx routes, fails over, and emits events. No human token
rotation required for the offline path.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from runtime.eventbus.bus import EventBus
from runtime.providers.base import Provider
from runtime.providers.manager import ProviderManager


class OnyxRuntime:
    """Autonomous provider router with EventBus telemetry."""

    def __init__(self, bus: Optional[EventBus] = None) -> None:
        self.bus = bus or EventBus()
        self.manager = ProviderManager(self.bus)
        self._started = time.monotonic()
        self._requests = 0
        self._failures = 0
        self.bus.subscribe("ProviderFailover", self._on_failover)
        self.bus.subscribe("ProviderUsed", self._on_used)

    # ── registration ──────────────────────────────────────────────
    def register(self, name: str, provider: Provider) -> None:
        self.manager.register(name, provider)

    def register_defaults(self) -> None:
        """Echo always; Grok CLI when present. No secrets touched."""
        from runtime.providers.echo import EchoProvider

        self.register("echo", EchoProvider(self.bus))
        try:
            from runtime.providers.grok_cli import cli_ready
            from runtime.providers.grok import GrokProvider

            if cli_ready():
                self.register("grok", GrokProvider(self.bus))
        except Exception:
            pass

    # ── routing ───────────────────────────────────────────────────
    def ask(self, message: str, preferred: Optional[str] = None) -> Dict[str, Any]:
        self._requests += 1
        ok = self.manager.send(message, preferred_provider=preferred)
        if not ok:
            self._failures += 1
        return {
            "ok": ok,
            "preferred": preferred,
            "requests": self._requests,
            "failures": self._failures,
            "uptime_s": round(time.monotonic() - self._started, 3),
        }

    def health(self) -> Dict[str, Any]:
        return {
            "providers": self.manager.health_all(),
            "requests": self._requests,
            "failures": self._failures,
            "uptime_s": round(time.monotonic() - self._started, 3),
        }

    # ── event hooks ───────────────────────────────────────────────
    def _on_failover(self, event) -> None:
        self._failures += 1

    def _on_used(self, event) -> None:
        pass
