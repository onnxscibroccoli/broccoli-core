from runtime.eventbus.bus import EventBus
from runtime.governor.engine import Governor
from runtime.state import RuntimeState


def test_governor_requests_restart_for_unhealthy_transport():
    bus = EventBus()
    state = RuntimeState()
    state.transition("RUNNING")

    restart_requests = []
    unhealthy_events = []
    healthy_events = []

    bus.subscribe("TRANSPORT_RESTART_REQUEST", lambda event: restart_requests.append(event.payload))
    bus.subscribe("TRANSPORT_UNHEALTHY", lambda event: unhealthy_events.append(event.payload))
    bus.subscribe("TRANSPORT_HEALTHY", lambda event: healthy_events.append(event.payload))

    Governor(bus, state)

    bus.publish(
        "TRANSPORT_HEALTH",
        {
            "transport": "clipboard",
            "running": False,
            "poll_interval": 0.01,
            "last_digest": None,
            "last_observed_at": None,
            "last_kind": None,
        },
        source="test",
    )

    assert len(unhealthy_events) == 1
    assert len(restart_requests) == 1
    assert restart_requests[0]["transport"] == "clipboard"
    assert restart_requests[0]["reason"] == "transport_not_running"

    bus.publish(
        "TRANSPORT_HEALTH",
        {
            "transport": "clipboard",
            "running": True,
            "poll_interval": 0.01,
            "last_digest": "abc",
            "last_observed_at": "2026-07-29T03:00:00+00:00",
            "last_kind": "command",
        },
        source="test",
    )

    assert len(healthy_events) == 1
