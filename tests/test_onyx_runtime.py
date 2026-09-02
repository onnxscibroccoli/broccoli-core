"""Offline tests for the Onyx runtime."""
from __future__ import annotations

from runtime.eventbus.bus import EventBus
from runtime.onyx import OnyxRuntime
from runtime.providers.echo import EchoProvider


def test_onyx_routes_to_echo_without_network():
    bus = EventBus()
    seen = []
    bus.subscribe("*", lambda e: seen.append(e.topic))
    onyx = OnyxRuntime(bus)
    onyx.register("echo", EchoProvider(bus))
    result = onyx.ask("hello from onyx")
    assert result["ok"] is True
    assert "ProviderRegistered" in seen
    assert "ProviderUsed" in seen
    health = onyx.health()
    assert health["providers"]["echo"]["provider"] == "echo"
    assert health["providers"]["echo"]["commercial"] is False
    assert health["failures"] == 0


def test_onyx_failover_emits_event():
    bus = EventBus()
    seen = []
    bus.subscribe("ProviderFailover", lambda e: seen.append(e.payload))

    class Boom(EchoProvider):
        def send(self, message, context=None):
            raise RuntimeError("boom")

    onyx = OnyxRuntime(bus)
    onyx.register("boom", Boom(bus))
    onyx.register("echo", EchoProvider(bus))
    result = onyx.ask("try me")
    assert result["ok"] is True
    assert len(seen) >= 1
    assert seen[0]["from"] == "boom"
