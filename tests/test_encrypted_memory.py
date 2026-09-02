"""Offline tests for the encrypted memory store."""
from runtime.memory.encrypted_store import EncryptedMemoryStore


def test_add_and_search(tmp_path, monkeypatch):
    monkeypatch.setenv("BROCCOLI_MEMORY_KEY", "")  # force file key path
    db = tmp_path / "mem.db"
    keyfile = tmp_path / "mem.key"
    monkeypatch.setattr("runtime.memory.encrypted_store.DEFAULT_DB", db)
    monkeypatch.setattr("runtime.memory.encrypted_store.DEFAULT_KEY_FILE", keyfile)
    store = EncryptedMemoryStore(db_path=db)
    store.add({"provider": "grok", "role": "user", "content": "hello bluetooth"})
    store.add({"provider": "grok", "role": "assistant", "content": "turning it on"})
    assert len(store.all()) == 2
    hits = store.search("bluetooth")
    assert len(hits) == 1
    assert "bluetooth" in hits[0]["content"]


def test_health(tmp_path, monkeypatch):
    monkeypatch.setattr("runtime.memory.encrypted_store.DEFAULT_DB", tmp_path / "m.db")
    monkeypatch.setattr("runtime.memory.encrypted_store.DEFAULT_KEY_FILE", tmp_path / "m.key")
    store = EncryptedMemoryStore(db_path=tmp_path / "m.db")
    h = store.health()
    assert "records" in h
