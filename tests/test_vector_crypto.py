from pathlib import Path

import pytest

from runtime.crypto_key import HAS_FERNET
from runtime.embed.pipeline import EmbedPipeline
from runtime.memory.search import HybridSearch
from runtime.memory.vectors import VectorStore


@pytest.mark.skipif(not HAS_FERNET, reason="cryptography not installed")
def test_encrypted_index_roundtrip(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BROCCOLI_MEMORY_KEY_FILE", str(tmp_path / "k.key"))
    monkeypatch.setenv("BROCCOLI_ENCRYPT_VECTORS", "1")
    store = VectorStore(tmp_path / "vectors", encrypt=True)
    EmbedPipeline(store).ingest("keep bluetooth enabled overnight")
    raw = (tmp_path / "vectors" / "index.jsonl").read_bytes()
    assert b"bluetooth" not in raw
    reloaded = VectorStore(tmp_path / "vectors", encrypt=True)
    assert reloaded.count() == 1
    hits = HybridSearch(reloaded).recall("enable bluetooth")
    assert hits
    assert "bluetooth" in hits[0]["text"].lower()


def test_plaintext_index_still_default(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("BROCCOLI_ENCRYPT_VECTORS", raising=False)
    store = VectorStore(tmp_path / "vectors")
    EmbedPipeline(store).ingest("dentist on tuesday")
    raw = (tmp_path / "vectors" / "index.jsonl").read_text(encoding="utf-8")
    assert "dentist" in raw
