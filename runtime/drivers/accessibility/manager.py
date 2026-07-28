from .backend import AccessibilityBackend
from .public_backend import PublicBackend
from .hidden_backend import HiddenBackend
from event_bus import EventBus

class AccessibilityManager:
    def __init__(self, bus: EventBus, preferred="public"):
        self.bus = bus
        self.preferred = preferred
        self.current_backend: AccessibilityBackend = None
        self.fallback_backend = PublicBackend()

    def initialize(self):
        try:
            if self.preferred == "hidden":
                self.current_backend = HiddenBackend()
            else:
                self.current_backend = PublicBackend()
            self.current_backend.initialize()
            self.bus.publish("BACKEND_STARTED", {"backend": self.preferred})
            return True
        except Exception:
            self.current_backend = self.fallback_backend
            self.current_backend.initialize()
            self.bus.publish("BACKEND_SWITCHED", {"to": "public"})
            return True

    def current_snapshot(self):
        return self.current_backend.current_snapshot()

    def health(self):
        return self.current_backend.health()
