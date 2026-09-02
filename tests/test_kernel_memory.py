"""Kernel remember + search_memory wiring. Offline."""
from pathlib import Path

from runtime.embed.pipeline import EmbedPipeline
from runtime.kernel import Kernel
from runtime.memory.vectors import VectorStore


def test_tick_remembers_intent(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BROCCOLI_VECTOR_ROOT", str(tmp_path / "vectors"))
    monkeypatch.setenv("BROCCOLI_MEMORY_PATH", str(tmp_path / "mem.json"))
    k = Kernel()
    out = k.tick("turn on bluetooth", dry_run=True)
    assert out["ok"] is True
    assert out["schema"] == "turn_on_bluetooth"
    assert out["remembered"]["encrypted"] is True
    assert out["remembered"]["embedded"] is True
    store = VectorStore(tmp_path / "vectors")
    assert store.count() >= 1


def test_search_memory_schema_returns_hits(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BROCCOLI_VECTOR_ROOT", str(tmp_path / "vectors"))
    monkeypatch.setenv("BROCCOLI_MEMORY_PATH", str(tmp_path / "mem.json"))
    store = VectorStore(tmp_path / "vectors")
    EmbedPipeline(store).ingest(
        "take morning medication with water",
        source="fixture",
        kind="note",
    )
    k = Kernel()
    out = k.tick("search memory for medication", dry_run=True)
    assert out["schema"] == "search_memory"
    assert "memory" in out
    assert out["memory"]["stub"] is False
    assert out["memory"]["hits"]
    assert "medication" in out["memory"]["hits"][0]["text"].lower()


def test_unknown_tick_still_ok(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BROCCOLI_VECTOR_ROOT", str(tmp_path / "vectors"))
    monkeypatch.setenv("BROCCOLI_MEMORY_PATH", str(tmp_path / "mem.json"))
    k = Kernel()
    out = k.tick("asdf qwer", dry_run=True)
    assert out["ok"] is True
    assert out["intent"] == "unknown"
