from runtime.eventbus.bus import EventBus
from runtime.providers.echo import EchoProvider
from runtime.providers.manager import ProviderManager


def test_echo_failover_and_events():
    bus = EventBus()
    seen = []
    bus.subscribe("*", lambda event: seen.append(event.topic))
    mgr = ProviderManager(bus)
    mgr.register("echo", EchoProvider(bus))
    assert mgr.send("hello") is True
    assert "ProviderRegistered" in seen
    assert "ProviderUsed" in seen
    health = mgr.health_all()
    assert health["echo"]["provider"] == "echo"
    assert health["echo"]["commercial"] is False
