"""Offline tests for the M3 embedded vector store."""
from __future__ import annotations

from pathlib import Path

from runtime.embed.local import HashingTrickEmbedder
from runtime.embed.pipeline import EmbedPipeline, chunk_text
from runtime.memory.cli import embed_text, recall
from runtime.memory.search import HybridSearch
from runtime.memory.vectors import VectorStore


def test_chunk_text_respects_overlap():
    text = "a" * 50
    chunks = chunk_text(text, max_chars=20, overlap=5)
    assert len(chunks) >= 3
    assert chunks[0] == "a" * 20


def test_embedder_is_deterministic_and_normalized():
    emb = HashingTrickEmbedder(dim=64)
    a = emb.embed("turn on bluetooth")
    b = emb.embed("turn on bluetooth")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9


def test_semantic_recall_ranks_bluetooth(tmp_path: Path):
    store = VectorStore(tmp_path)
    pipe = EmbedPipeline(store, HashingTrickEmbedder())
    pipe.ingest("turn on bluetooth from the settings panel", source="fixture", kind="intent")
    pipe.ingest("remind me to take medication at 8am", source="fixture", kind="intent")
    pipe.ingest("open the calendar for next Tuesday", source="fixture", kind="intent")
    hits = HybridSearch(store).recall("how do I enable bluetooth", top_k=2)
    assert hits
    assert "bluetooth" in hits[0]["text"].lower()


def test_incremental_skip_duplicate(tmp_path: Path):
    store = VectorStore(tmp_path)
    pipe = EmbedPipeline(store)
    first = pipe.ingest("same sentence twice")
    second = pipe.ingest("same sentence twice")
    assert first["added"] == 1
    assert second["added"] == 0
    assert second["skipped"] == 1
    assert store.count() == 1


def test_cli_roundtrip(tmp_path: Path):
    embed_text("schedule dentist appointment next week", root=tmp_path)
    hits = recall("dentist visit", root=tmp_path, top_k=3)
    assert hits
    assert "dentist" in hits[0]["text"].lower()


def test_persist_reload(tmp_path: Path):
    store = VectorStore(tmp_path)
    EmbedPipeline(store).ingest("bluetooth radio should stay on")
    reloaded = VectorStore(tmp_path)
    assert reloaded.count() == 1
    hits = HybridSearch(reloaded).recall("keep bluetooth enabled")
    assert hits
