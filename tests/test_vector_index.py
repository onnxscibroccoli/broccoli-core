"""Offline tests for the local vector index."""
from runtime.memory.vector_index import VectorIndex


def test_search_ranks_relevant(tmp_path):
    idx = VectorIndex()
    idx.add("1", "turn on bluetooth now")
    idx.add("2", "remind me about the meeting")
    idx.add("3", "bluetooth is on")
    hits = idx.search("bluetooth", top_k=2)
    assert len(hits) >= 1
    assert hits[0]["id"] in ("1", "3")


def test_health():
    idx = VectorIndex()
    idx.add("a", "hello world")
    h = idx.health()
    assert h["documents"] == 1
