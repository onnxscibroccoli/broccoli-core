"""Termux-safe embedder. No network. No third-party model by default.

Hashing-trick bag of char-ngrams + tokens. Deterministic. Fixed dimension.
ONNX / sentence-transformers can replace LocalEmbedder later without
changing the store contract.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable, List, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


def _ngrams(text: str, n: int) -> Iterable[str]:
    compact = re.sub(r"\s+", " ", (text or "").lower()).strip()
    if len(compact) < n:
        if compact:
            yield compact
        return
    for i in range(len(compact) - n + 1):
        yield compact[i : i + n]


def _bucket(feature: str, dim: int) -> int:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "little") % dim


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


class HashingTrickEmbedder:
    """Fixed-dimension hashing embedder. Works with zero extra packages."""

    name = "hashing-trick-v1"

    def __init__(self, dim: int = 256) -> None:
        if dim < 8:
            raise ValueError("dim must be >= 8")
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        raw = (text or "").strip()
        if not raw:
            return vec
        for tok in _tokens(raw):
            vec[_bucket("t:" + tok, self.dim)] += 1.0
        for n in (3, 4, 5):
            weight = 0.5 if n == 3 else 0.35
            for gram in _ngrams(raw, n):
                vec[_bucket(f"n{n}:" + gram, self.dim)] += weight
        return _l2_normalize(vec)

    def embed_many(self, texts: Sequence[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]


LocalEmbedder = HashingTrickEmbedder
