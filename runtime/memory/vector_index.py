"""Local TF-IDF vector index (M3).

Pure-Python / numpy bag-of-words index. No external embedding model
required for the fallback path; an ONNX embedding model can be plugged
in later via the same interface. Keeps everything offline and
searchable on a phone.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Tuple

try:
    import numpy as np  # type: ignore
    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    _HAS_NUMPY = False

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


class VectorIndex:
    """Tiny TF-IDF index over in-memory documents."""

    def __init__(self) -> None:
        self._docs: List[Dict[str, Any]] = []
        self._df: Dict[str, int] = defaultdict(int)
        self._dirty = True
        self._tfidf: Any = None

    def add(self, doc_id: str, text: str, meta: Optional[Dict[str, Any]] = None) -> None:
        self._docs.append({"id": doc_id, "text": text or "", "meta": meta or {}})
        for t in set(_tokenize(text)):
            self._df[t] += 1
        self._dirty = True

    def _build(self) -> None:
        n = len(self._docs)
        if n == 0 or not _HAS_NUMPY:
            self._tfidf = None
            self._dirty = False
            return
        vocab = sorted(self._df.keys())
        vidx = {t: i for i, t in enumerate(vocab)}
        mat = np.zeros((n, len(vocab)), dtype=float)
        for i, d in enumerate(self._docs):
            tf = Counter(_tokenize(d["text"]))
            for t, c in tf.items():
                if t in vidx:
                    idf = math.log((n + 1) / (self._df[t] + 1)) + 1.0
                    mat[i, vidx[t]] = c * idf
        # l2 normalize rows
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self._tfidf = mat / norms
        self._dirty = False

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self._dirty:
            self._build()
        if not _HAS_NUMPY or self._tfidf is None or not self._docs:
            # crude fallback: substring match
            q = (query or "").lower()
            return [d for d in self._docs if q in d["text"].lower()][:top_k]
        qv = np.zeros((self._tfidf.shape[1],), dtype=float)
        tf = Counter(_tokenize(query))
        n = len(self._docs)
        for t, c in tf.items():
            # approximate idf from df
            idf = math.log((n + 1) / (self._df.get(t, 0) + 1)) + 1.0
            # find column
            # rebuild vocab index cheaply
            pass
        # simpler: recompute query vector against stored df
        vocab = sorted(self._df.keys())
        vidx = {t: i for i, t in enumerate(vocab)}
        for t, c in tf.items():
            if t in vidx:
                idf = math.log((n + 1) / (self._df[t] + 1)) + 1.0
                qv[vidx[t]] = c * idf
        nrm = np.linalg.norm(qv)
        if nrm > 0:
            qv = qv / nrm
        scores = self._tfidf @ qv
        order = np.argsort(-scores)[:top_k]
        out = []
        for i in order:
            if scores[i] <= 0:
                continue
            d = dict(self._docs[int(i)])
            d["score"] = float(scores[i])
            out.append(d)
        return out

    def health(self) -> Dict[str, Any]:
        return {
            "numpy_available": _HAS_NUMPY,
            "documents": len(self._docs),
            "vocab": len(self._df),
        }
