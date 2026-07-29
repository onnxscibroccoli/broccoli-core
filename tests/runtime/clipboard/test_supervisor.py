from runtime.clipboard.supervisor import register_clipboard_supervisor
from runtime.governor.engine import Governor
from runtime.eventbus.bus import EventBus
from runtime.state import RuntimeState


class FakeBridge:
    def __init__(self):
        self.started = 0
        self.stopped = 0
        self._running = False

    def health(self):
        return {
            "running": self._running,
            "poll_interval": 0.01,
            "last_digest": None,
            "last_observed_at": None,
            "last_kind": None,
        }

    def stop(self):
        self.stopped += 1
        self._running = False

    def start(self):
        self.started += 1
        self._running = True
        return self


def test_governor_requests_restart_when_clipboard_bridge_unhealthy():
    bus = EventBus()
    state = RuntimeState()
    state.transition("RUNNING")

    restart_requests = []
    unhealthy_events = []
    healthy_events = []

    bus.subscribe("CLIPBOARD_BRIDGE_RESTART_REQUEST", lambda event: restart_requests.append(event.payload))
    bus.subscribe("CLIPBOARD_BRIDGE_UNHEALTHY", lambda event: unhealthy_events.append(event.payload))
    bus.subscribe("CLIPBOARD_BRIDGE_HEALTHY", lambda event: healthy_events.append(event.payload))

    Governor(bus, state)

    bus.publish(
        "CLIPBOARD_BRIDGE_HEALTH",
        {
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
    assert restart_requests[0]["bridge_health"]["running"] is False

    bus.publish(
        "CLIPBOARD_BRIDGE_HEALTH",
        {
            "running": True,
            "poll_interval": 0.01,
            "last_digest": "abc",
            "last_observed_at": "2026-07-29T03:00:00+00:00",
            "last_kind": "command",
        },
        source="test",
    )

    assert len(healthy_events) == 1


def test_clipboard_supervisor_restarts_bridge_and_emits_recovery():
    bus = EventBus()
    bridge = FakeBridge()

    recovered = []
    failed = []

    bus.subscribe("CLIPBOARD_BRIDGE_RECOVERED", lambda event: recovered.append(event.payload))
    bus.subscribe("CLIPBOARD_BRIDGE_RECOVERY_FAILED", lambda event: failed.append(event.payload))

    register_clipboard_supervisor(bus, bridge)

    bus.publish(
        "CLIPBOARD_BRIDGE_RESTART_REQUEST",
        {"reason": "bridge_not_running"},
        source="Governor",
    )

    assert bridge.stopped == 1
    assert bridge.started == 1
    assert failed == []
    assert len(recovered) == 1
    assert recovered[0]["after"]["running"] is True
