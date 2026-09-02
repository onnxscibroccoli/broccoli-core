"""Pick an embedder. Hashing is default. ONNX only if a local model file loads."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from runtime.embed.local import HashingTrickEmbedder


def get_embedder(dim: int = 256) -> Any:
    path = os.environ.get("BROCCOLI_ONNX_EMBED", "").strip()
    if path and Path(path).is_file():
        try:
            from runtime.embed.onnx_embed import OnnxEmbedder

            emb = OnnxEmbedder(path, dim=dim)
            if emb.usable:
                return emb
        except Exception:
            pass
    return HashingTrickEmbedder(dim=dim)
