from runtime.transports.provider_transport import ProviderTransport


class FakeProvider:
    def __init__(self):
        self.initialized = 0
        self.shutdowns = 0

    def initialize(self):
        self.initialized += 1

    def shutdown(self):
        self.shutdowns += 1

    def health(self):
        return {"provider_ready": True}


def test_provider_transport_start_stop_and_health():
    provider = FakeProvider()
    transport = ProviderTransport("grok", provider)

    transport.start()
    health = transport.health()
    transport.stop()

    assert provider.initialized == 1
    assert provider.shutdowns == 1
    assert health["running"] is True
    assert health["provider_ready"] is True
    assert transport.health()["running"] is False
