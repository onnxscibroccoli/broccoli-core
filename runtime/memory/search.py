"""Hybrid retrieval: cosine + lexical bonus."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from runtime.embed.local import HashingTrickEmbedder
from runtime.memory.vectors import VectorStore


def _lexical_bonus(query: str, text: str) -> float:
    q = (query or "").lower().strip()
    t = (text or "").lower()
    if not q or not t:
        return 0.0
    if q in t:
        return 0.15
    tokens = [tok for tok in q.split() if len(tok) > 2]
    if not tokens:
        return 0.0
    hits = sum(1 for tok in tokens if tok in t)
    return 0.08 * (hits / len(tokens))


class HybridSearch:
    def __init__(self, store: VectorStore, embedder: Optional[HashingTrickEmbedder] = None) -> None:
        self.store = store
        self.embedder = embedder or HashingTrickEmbedder()

    def recall(
        self,
        query: str,
        *,
        top_k: int = 5,
        min_score: float = 0.05,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        raw = (query or "").strip()
        if not raw:
            return []
        qv = self.embedder.embed(raw)
        hits = self.store.search(qv, top_k=max(top_k * 3, top_k), min_score=0.0, where=where)
        for hit in hits:
            hit["score"] = float(hit["score"]) + _lexical_bonus(raw, str(hit.get("text") or ""))
        hits = [h for h in hits if float(h["score"]) >= min_score]
        hits.sort(key=lambda r: r["score"], reverse=True)
        return hits[:top_k]
