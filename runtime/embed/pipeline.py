"""Chunk → embed → upsert. Incremental. Offline."""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, List, Optional

from runtime.embed.factory import get_embedder
from runtime.embed.local import HashingTrickEmbedder
from runtime.memory.vectors import VectorRecord, VectorStore


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 160) -> List[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    if max_chars <= 0:
        raise ValueError("max_chars must be > 0")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be >= 0 and < max_chars")
    if len(raw) <= max_chars:
        return [raw]
    chunks: List[str] = []
    start = 0
    while start < len(raw):
        end = min(len(raw), start + max_chars)
        piece = raw[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(raw):
            break
        start = end - overlap
    return chunks


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:24]


class EmbedPipeline:
    def __init__(
        self,
        store: VectorStore,
        embedder: Optional[HashingTrickEmbedder] = None,
        max_chars: int = 1200,
        overlap: int = 160,
    ) -> None:
        self.store = store
        self.embedder = embedder or get_embedder()
        self.max_chars = max_chars
        self.overlap = overlap

    def ingest(
        self,
        text: str,
        *,
        source: str = "broccoli",
        kind: str = "note",
        doc_id: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        chunks = chunk_text(text, self.max_chars, self.overlap)
        added = 0
        skipped = 0
        ids: List[str] = []
        base = doc_id or content_hash(text)
        for i, chunk in enumerate(chunks):
            rec_id = f"{base}:{i}"
            digest = content_hash(chunk)
            if self.store.has_hash(digest):
                skipped += 1
                continue
            vector = self.embedder.embed(chunk)
            rec = VectorRecord(
                id=rec_id,
                text=chunk,
                vector=vector,
                kind=kind,
                source=source,
                content_hash=digest,
                meta=dict(meta or {}),
            )
            self.store.upsert(rec)
            added += 1
            ids.append(rec_id)
        if added:
            self.store.flush()
        return {"ok": True, "added": added, "skipped": skipped, "chunks": len(chunks), "ids": ids}

    def ingest_many(self, items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        totals = {"ok": True, "added": 0, "skipped": 0, "docs": 0}
        for item in items:
            result = self.ingest(
                str(item.get("text") or ""),
                source=str(item.get("source") or "broccoli"),
                kind=str(item.get("kind") or "note"),
                doc_id=item.get("doc_id"),
                meta=item.get("meta") if isinstance(item.get("meta"), dict) else None,
            )
            totals["added"] += int(result["added"])
            totals["skipped"] += int(result["skipped"])
            totals["docs"] += 1
        return totals
