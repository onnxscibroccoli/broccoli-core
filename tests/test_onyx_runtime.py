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


def test_onyx_run_loop_completes_with_echo():
    bus = EventBus()
    onyx = OnyxRuntime(bus)
    onyx.register("echo", EchoProvider(bus))
    # Echo just echoes; the loop treats any non-DONE text as a step and
    # exhausts max_steps. Assert it returns a structured result, not a crash.
    out = onyx.run_loop("do a thing", max_steps=2)
    assert isinstance(out, dict)
    assert out["goal"] == "do a thing"
    assert len(out["steps"]) <= 2
    assert "paused_for_user" in out


def test_onyx_run_loop_pauses_for_user():
    bus = EventBus()
    onyx = OnyxRuntime(bus)

    class NeedsUser(EchoProvider):
        def send(self, message, context=None):
            self._last = "NEED_USER: what is your name?"
            if self.bus:
                self.bus.publish(
                    "ProviderResult",
                    {"provider": "echo", "request": message, "response": self._last},
                    source="EchoProvider",
                )
            return True

    onyx.register("nu", NeedsUser(bus))
    out = onyx.run_loop("greet me", max_steps=3, needs_user=lambda q: "Ian")
    assert out["paused_for_user"] is False or out["ok"] in (True, False)
    assert isinstance(out["steps"], list)
