from runtime.transports.plugin_loader_transport import PluginLoaderTransport


class FakePluginLoader:
    def __init__(self):
        self.load_calls = 0

    def load(self):
        self.load_calls += 1


def test_plugin_loader_transport_lifecycle():
    loader = FakePluginLoader()
    transport = PluginLoaderTransport(loader)

    assert transport.health()["running"] is False
    assert transport.health()["loaded"] is False

    transport.start()
    first = transport.health()

    assert loader.load_calls == 1
    assert first["running"] is True
    assert first["loaded"] is True

    transport.start()
    second = transport.health()

    assert loader.load_calls == 1
    assert second["running"] is True

    transport.stop()
    assert transport.health()["running"] is False
