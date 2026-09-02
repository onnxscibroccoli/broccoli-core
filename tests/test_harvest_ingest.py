"""Harvest JSONL → vector store. Offline."""
import json
from pathlib import Path

from runtime.ingest.harvest import embed_harvest, records_from_object
from runtime.memory.search import HybridSearch
from runtime.memory.vectors import VectorStore


def test_records_from_harvest_blob():
    blob = {
        "thread_id": "abc123",
        "tail": "ignored when lines exist",
        "lines": ["turn on bluetooth", "", "remind me about meds"],
    }
    recs = records_from_object(blob)
    assert len(recs) == 2
    assert recs[0]["doc_id"] == "abc123:0"
    assert recs[1]["text"] == "remind me about meds"


def test_embed_harvest_jsonl(tmp_path: Path):
    harvest = tmp_path / "harvest"
    harvest.mkdir()
    rec = {
        "thread_id": "t1",
        "lines": [
            "how do I enable bluetooth on this phone",
            "schedule dentist next Tuesday",
        ],
    }
    (harvest / "t1.jsonl").write_text(json.dumps(rec) + "\n", encoding="utf-8")
    result = embed_harvest(harvest, store_root=tmp_path / "vectors")
    assert result["ok"] is True
    assert result["added"] == 2
    store = VectorStore(tmp_path / "vectors")
    hits = HybridSearch(store).recall("enable bluetooth")
    assert hits
    assert "bluetooth" in hits[0]["text"].lower()


def test_embed_harvest_skips_duplicates(tmp_path: Path):
    harvest = tmp_path / "harvest"
    harvest.mkdir()
    rec = {"thread_id": "t2", "lines": ["same line twice"]}
    (harvest / "t2.jsonl").write_text(json.dumps(rec) + "\n" + json.dumps(rec) + "\n", encoding="utf-8")
    first = embed_harvest(harvest, store_root=tmp_path / "vectors")
    second = embed_harvest(harvest, store_root=tmp_path / "vectors")
    assert first["added"] == 1
    assert second["added"] == 0
    assert second["skipped"] >= 1
