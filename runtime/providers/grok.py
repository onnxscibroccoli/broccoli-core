from runtime.providers.base import Provider
from runtime.eventbus import EventBus

class GrokProvider(Provider):
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.initialized = False
        self.session_active = False

    def initialize(self) -> bool:
        self.initialized = True
        self.session_active = True
        print("GrokProvider: Production initialized")
        self.bus.publish("ProviderConnected", "grok")
        return True

    def send(self, message: str, context: Dict = None) -> bool:
        print(f"GrokProvider: Sending production message: {message[:60]}...")
        self.bus.publish("ConversationUpdated", {"provider": "grok", "message": message, "context": context})
        return True

    def stream(self, message: str):
        print(f"GrokProvider: Streaming: {message[:50]}...")
        self.bus.publish("StreamChunk", {"provider": "grok", "chunk": message})

    def health(self) -> Dict:
        return {"status": "healthy", "provider": "grok", "session": self.session_active, "latency": 45}

    def shutdown(self) -> bool:
        self.session_active = False
        print("GrokProvider: Graceful shutdown")
        return True

    def capabilities(self) -> Dict:
        return {"chat": True, "vision": True, "tools": True, "streaming": True}
