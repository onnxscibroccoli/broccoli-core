"""Optional ONNX embedder. Falls back to hashing if the model cannot run.

A model file on disk is not enough. We only mark the embedder usable when
onnxruntime loads the session AND the output vector length matches `dim`.
Otherwise hashing stays in charge so the store does not mix dimensions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, List, Sequence

from runtime.embed.local import HashingTrickEmbedder


class OnnxEmbedder:
    name = "onnx-embed"

    def __init__(self, model_path: str | Path, dim: int = 256) -> None:
        self.model_path = Path(model_path)
        self.dim = dim
        self.fallback = HashingTrickEmbedder(dim=dim)
        self._session = None
        self._input_name = ""
        self._error = ""
        self.usable = False
        self._try_load()

    def _try_load(self) -> None:
        if not self.model_path.is_file():
            self._error = "missing model"
            return
        try:
            import onnxruntime as ort  # type: ignore
        except Exception as exc:
            self._error = f"onnxruntime unavailable: {exc}"
            return
        try:
            self._session = ort.InferenceSession(str(self.model_path))
            inputs = self._session.get_inputs()
            outputs = self._session.get_outputs()
            if not inputs or not outputs:
                self._error = "model has no io"
                self._session = None
                return
            self._input_name = inputs[0].name
            self._error = "session loaded; no tokenizer bridge — hashing used"
            self.usable = False
        except Exception as exc:
            self._error = str(exc)
            self._session = None

    def embed(self, text: str) -> List[float]:
        return self.fallback.embed(text)

    def embed_many(self, texts: Sequence[str]) -> List[List[float]]:
        return [self.embed(t) for t in texts]

    def health(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "model_path": str(self.model_path),
            "session": self._session is not None,
            "usable": self.usable,
            "dim": self.dim,
            "error": self._error,
            "active": "hashing-trick-v1",
        }
