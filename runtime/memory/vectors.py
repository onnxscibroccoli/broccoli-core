"""File-backed vector store. Embedded. Offline. Incremental.

Layout:
  <root>/index.jsonl   one record per line
  mode 600 when possible

Similarity: cosine. Brute force is intentional — phone-scale corpora
(tens of thousands of chunks) stay under 10ms in CPython.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return float(sum(x * y for x, y in zip(a, b)))


def _meta_matches(meta: Dict[str, Any], where: Optional[Dict[str, Any]]) -> bool:
    if not where:
        return True
    for key, expected in where.items():
        if meta.get(key) != expected:
            return False
    return True


@dataclass
class VectorRecord:
    id: str
    text: str
    vector: List[float]
    kind: str = "note"
    source: str = "broccoli"
    content_hash: str = ""
    ts: float = field(default_factory=time.time)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "vector": self.vector,
            "kind": self.kind,
            "source": self.source,
            "content_hash": self.content_hash,
            "ts": self.ts,
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VectorRecord":
        return cls(
            id=str(data.get("id") or ""),
            text=str(data.get("text") or ""),
            vector=[float(x) for x in (data.get("vector") or [])],
            kind=str(data.get("kind") or "note"),
            source=str(data.get("source") or "broccoli"),
            content_hash=str(data.get("content_hash") or ""),
            ts=float(data.get("ts") or 0.0),
            meta=dict(data.get("meta") or {}),
        )


class VectorStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "index.jsonl"
        self._rows: List[VectorRecord] = []
        self._by_id: Dict[str, int] = {}
        self._hashes: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError:
            return
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = VectorRecord.from_dict(json.loads(line))
            except Exception:
                continue
            self._index_row(rec)

    def _index_row(self, rec: VectorRecord) -> None:
        if rec.id in self._by_id:
            idx = self._by_id[rec.id]
            old = self._rows[idx]
            if old.content_hash:
                self._hashes.discard(old.content_hash)
            self._rows[idx] = rec
        else:
            self._by_id[rec.id] = len(self._rows)
            self._rows.append(rec)
        if rec.content_hash:
            self._hashes.add(rec.content_hash)

    def has_hash(self, digest: str) -> bool:
        return bool(digest) and digest in self._hashes

    def upsert(self, rec: VectorRecord) -> None:
        if not rec.id:
            raise ValueError("record id is required")
        if rec.ts <= 0:
            rec.ts = time.time()
        self._index_row(rec)

    def flush(self) -> None:
        tmp = self.path.with_suffix(".jsonl.tmp")
        payload = "\n".join(json.dumps(r.to_dict(), separators=(",", ":")) for r in self._rows)
        if payload:
            payload += "\n"
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    def search(
        self,
        query_vector: List[float],
        *,
        top_k: int = 5,
        min_score: float = 0.0,
        where: Optional[Dict[str, Any]] = None,
        kinds: Optional[Iterable[str]] = None,
    ) -> List[Dict[str, Any]]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        kind_set = set(kinds) if kinds else None
        scored: List[Dict[str, Any]] = []
        for rec in self._rows:
            if kind_set is not None and rec.kind not in kind_set:
                continue
            if not _meta_matches(rec.meta, where):
                continue
            score = cosine(query_vector, rec.vector)
            if score <= min_score:
                continue
            scored.append(
                {
                    "id": rec.id,
                    "text": rec.text,
                    "kind": rec.kind,
                    "source": rec.source,
                    "score": score,
                    "ts": rec.ts,
                    "meta": dict(rec.meta),
                }
            )
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        return len(self._rows)

    def health(self) -> Dict[str, Any]:
        dim = len(self._rows[0].vector) if self._rows else 0
        return {
            "path": str(self.path),
            "documents": len(self._rows),
            "dim": dim,
            "backend": "jsonl-cosine",
        }
