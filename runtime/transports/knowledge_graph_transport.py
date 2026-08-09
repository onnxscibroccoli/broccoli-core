from __future__ import annotations

from runtime.memory.knowledge_graph import KnowledgeGraph


class KnowledgeGraphTransport:
    """Expose KnowledgeGraph as a managed transport without changing graph internals."""

    def __init__(self, knowledge_graph: KnowledgeGraph, name: str = "knowledge_graph"):
        self.name = name
        self.knowledge_graph = knowledge_graph
        self._running = False
        self._last_snapshot = None

    def start(self):
        self._running = True
        return self

    def stop(self):
        self._running = False
        return self

    def health(self):
        snapshot = self.knowledge_graph.collect_health()
        self._last_snapshot = snapshot
        return {
            "running": self._running,
            "snapshot": snapshot.to_dict(),
        }
