from runtime.drivers.accessibility import driver as driver_mod


class FakeBus:
    def __init__(self):
        self.subscriptions = []
        self.events = []

    def subscribe(self, topic, callback):
        self.subscriptions.append((topic, callback))

    def publish(self, topic, payload=None, source="unknown"):
        event = {"topic": topic, "payload": payload or {}, "source": source}
        self.events.append(event)
        return event


class FakeManager:
    def __init__(self, bus, preferred="public"):
        self.bus = bus
        self.preferred = preferred

    def initialize(self):
        return True

    def current_snapshot(self):
        return {"node_count": 0}

    def health(self):
        return {"manager_ready": True}


class FakeObserver:
    def __init__(self, bus=None, metrics=None, logger=None):
        self.running = False
        self.health_calls = 0

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def health(self):
        self.health_calls += 1
        return {
            "running": self.running,
            "cache_nodes": 0,
            "cache_stats": {},
            "observer_stats": {"health_calls": self.health_calls},
        }

    def observe(self, raw_event):
        return []


def test_accessibility_driver_exposes_transport_lifecycle():
    original_manager = driver_mod.AccessibilityManager
    original_observer = driver_mod.AccessibilityObserver
    driver_mod.AccessibilityManager = FakeManager
    driver_mod.AccessibilityObserver = FakeObserver

    try:
        bus = FakeBus()
        driver = driver_mod.AccessibilityDriver(bus)

        assert any(topic == "TICK" for topic, _ in bus.subscriptions)
        assert driver.health()["running"] is False

        driver.start()
        health = driver.health()
        assert health["running"] is True
        assert health["observer"]["running"] is True

        driver.stop()
        assert driver.health()["running"] is False
    finally:
        driver_mod.AccessibilityManager = original_manager
        driver_mod.AccessibilityObserver = original_observer
