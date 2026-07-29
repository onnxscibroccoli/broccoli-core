from runtime.memory.knowledge_graph import KnowledgeGraph
from runtime.transports.knowledge_graph_transport import KnowledgeGraphTransport


class FakeBus:
    def subscribe(self, *args, **kwargs):
        return None

    def publish(self, *args, **kwargs):
        return None


def test_knowledge_graph_transport_lifecycle(tmp_path):
    graph = KnowledgeGraph(bus=FakeBus(), root=tmp_path)
    transport = KnowledgeGraphTransport(graph)

    health = transport.health()
    assert health["running"] is False
    assert "snapshot" in health

    transport.start()
    assert transport.health()["running"] is True

    transport.stop()
    assert transport.health()["running"] is False
