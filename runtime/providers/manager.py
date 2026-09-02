"""Provider registry with failover and EventBus hooks.

Does not assume Grok. Preferred name is a hint, not a hard dependency.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from runtime.eventbus import EventBus
from runtime.providers.base import Provider


class ProviderManager:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.providers: Dict[str, Provider] = {}
        self.order: List[str] = []

    def register(self, name: str, provider: Provider) -> None:
        self.providers[name] = provider
        if name not in self.order:
            self.order.append(name)
        self.bus.publish(
            "ProviderRegistered",
            {"name": name, "capabilities": _safe_caps(provider)},
            source="ProviderManager",
        )

    def send(self, message: str, preferred_provider: Optional[str] = None) -> bool:
        for name in self._candidates(preferred_provider):
            provider = self.providers[name]
            try:
                if hasattr(provider, "initialize"):
                    provider.initialize()
                ok = provider.send(message)
            except Exception as exc:
                self.bus.publish(
                    "ProviderFailover",
                    {"from": name, "error": str(exc)},
                    source="ProviderManager",
                )
                continue
            if ok:
                self.bus.publish(
                    "ProviderUsed",
                    {"name": name, "preferred": preferred_provider},
                    source="ProviderManager",
                )
                return True
            self.bus.publish(
                "ProviderFailover",
                {"from": name, "error": "send returned False"},
                source="ProviderManager",
            )
        self.bus.publish("ProviderError", {"error": "all providers failed"}, source="ProviderManager")
        return False

    def health_all(self) -> Dict[str, Any]:
        out = {}
        for name, provider in self.providers.items():
            try:
                out[name] = provider.health()
            except Exception as exc:
                out[name] = {"status": "error", "error": str(exc)}
        return out

    def _candidates(self, preferred: Optional[str]) -> Iterable[str]:
        names = list(self.order)
        if preferred and preferred in self.providers:
            names = [preferred] + [n for n in names if n != preferred]
        return names


def _safe_caps(provider: Provider) -> Dict[str, bool]:
    try:
        return provider.capabilities()
    except Exception:
        return {}
