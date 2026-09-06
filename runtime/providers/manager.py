"""Provider registry with failover and EventBus hooks.

Does not assume Grok. Preferred name is a hint, not a hard dependency.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from runtime.account_pool import AccountPool
from runtime.eventbus import EventBus
from runtime.policy.execution_guard import ExecutionGuard
from runtime.providers.base import Provider


class ProviderManager:
    def __init__(
        self,
        bus: EventBus,
        account_pool: Optional[AccountPool] = None,
        execution_guard: Optional[ExecutionGuard] = None,
    ) -> None:
        self.bus = bus
        self.account_pool = account_pool
        self.execution_guard = execution_guard
        self.providers: Dict[str, Provider] = {}
        self.order: List[str] = []
        self.account_providers: Dict[str, Provider] = {}

    def register(self, name: str, provider: Provider) -> None:
        self.providers[name] = provider
        if name not in self.order:
            self.order.append(name)
        self.bus.publish(
            "ProviderRegistered",
            {"name": name, "capabilities": _safe_caps(provider)},
            source="ProviderManager",
        )

    def register_account(self, account_id: str, provider: Provider) -> None:
        """Bind an authorized account-pool entry to its provider adapter."""
        if self.account_pool is None:
            raise RuntimeError("account_pool is required for account registration")

        account = next(
            (item for item in self.account_pool.accounts
             if item.account_id == account_id),
            None,
        )
        if account is None:
            raise KeyError(account_id)

        self.account_providers[account_id] = provider
        self.bus.publish(
            "AccountRegistered",
            {
                "account_id": account_id,
                "provider": account.provider,
            },
            source="ProviderManager",
        )

    def send(self, message: str, preferred_provider: Optional[str] = None, *, initial_fill: bool = False, verb: str = "SEND") -> bool:
        # Authorization MUST precede provider preference, account
        # selection, initialization, failover, and provider execution.
        # Keep this outside provider try/except so GONE cannot become
        # ordinary provider failover.
        if self.execution_guard is not None:
            self.execution_guard.authorize(
                initial_fill=initial_fill,
                verb=verb,
            )

        if self.account_pool is not None and self.account_providers:
            return self._send_with_account_pool(
                message,
                preferred_provider,
            )

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

    def _send_with_account_pool(
        self,
        message: str,
        preferred_provider: Optional[str] = None,
    ) -> bool:
        """Send using the next usable authorized account/provider pair."""

        selected = self.account_pool.select(
            preferred_provider=preferred_provider,
        )

        if selected is None:
            self.bus.publish(
                "ProviderError",
                {"error": "all account/provider pairs unavailable"},
                source="ProviderManager",
            )
            return False

        provider = self.account_providers.get(selected.account_id)

        if provider is None:
            self.bus.publish(
                "ProviderError",
                {
                    "error": "selected account has no registered provider",
                    "account_id": selected.account_id,
                },
                source="ProviderManager",
            )
            return False

        try:
            if hasattr(provider, "initialize"):
                provider.initialize()
            ok = provider.send(message)
        except Exception as exc:
            ok = False
            error = str(exc)
        else:
            error = "send returned False" if not ok else ""

        if ok:
            self.bus.publish(
                "ProviderUsed",
                {
                    "name": selected.provider,
                    "account_id": selected.account_id,
                    "preferred": preferred_provider,
                },
                source="ProviderManager",
            )
            return True

        self.account_pool.mark_unavailable(selected.account_id)

        self.bus.publish(
            "ProviderFailover",
            {
                "from": selected.provider,
                "account_id": selected.account_id,
                "error": error,
            },
            source="ProviderManager",
        )

        # Fail over once to the next normal pool position. Do not repeatedly
        # re-apply the preferred-provider bias.
        return self._send_with_account_pool(message, preferred_provider=None)

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
