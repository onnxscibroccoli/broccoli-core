from typing import Dict
from event_bus import EventBus

class ProviderManager:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.providers = {}

    def register(self, name, provider):
        self.providers[name] = provider
        print(f"ProviderManager: Registered {name}")

    def send(self, message: str, preferred_provider="grok"):
        if preferred_provider in self.providers:
            return self.providers[preferred_provider].send(message)
        return False

    def health_all(self):
        return {name: p.health() for name, p in self.providers.items()}
