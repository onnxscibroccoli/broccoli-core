"""ONNX Runtime integration for Broccoli Core.

Loads a local ONNX model for intent classification / embedding and falls
back to a pure-Python keyword matcher when no model file is present.
This is the REAL ONNX integration (distinct from the Onyx router).

Design goals:
  - Zero network, zero commercial gate, zero secrets.
  - Graceful degradation: missing onnxruntime or missing model file
    never crashes the runtime; it just uses the keyword fallback.
  - Termux-friendly: onnxruntime CPU builds are small; the fallback
    means even a stock Termux python works.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

log = logging.getLogger("broccoli.onnx")

try:
    import numpy as np  # type: ignore
    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    np = None  # type: ignore
    _HAS_NUMPY = False

try:
    import onnxruntime as ort  # type: ignore
    _HAS_ORT = True
except Exception:  # pragma: no cover
    ort = None  # type: ignore
    _HAS_ORT = False


# Default intents the keyword fallback recognises. Real ONNX models can
# emit any of these labels; the fallback maps phrases to them.
KNOWN_INTENTS: List[str] = [
    "toggle_bluetooth",
    "set_reminder",
    "open_calendar",
    "search_memory",
    "report_status",
    "unknown",
]

# Phrase -> intent for the offline fallback. Kept tiny on purpose.
_FALLBACK_RULES: List[Tuple[str, str]] = [
    ("bluetooth", "toggle_bluetooth"),
    ("wifi", "toggle_bluetooth"),  # placeholder; real rules expand later
    ("remind", "set_reminder"),
    ("reminder", "set_reminder"),
    ("calendar", "open_calendar"),
    ("schedule", "open_calendar"),
    ("remember", "search_memory"),
    ("recall", "search_memory"),
    ("search", "search_memory"),
    ("how am i", "report_status"),
    ("status", "report_status"),
]


class OnnxIntentClassifier:
    """Classify a user utterance into an intent label.

    Prefers a loaded ONNX session. Falls back to keyword rules. Never
    raises on missing deps — returns ('unknown', 0.0) instead.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        providers: Optional[List[str]] = None,
    ) -> None:
        self.model_path = Path(model_path) if model_path else None
        self.session: Any = None
        self._load_error: Optional[str] = None
        if self.model_path and self.model_path.is_file() and _HAS_ORT:
            try:
                so = ort.SessionOptions()
                so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                self.session = ort.InferenceSession(
                    str(self.model_path),
                    sess_options=so,
                    providers=providers or ["CPUExecutionProvider"],
                )
                log.info("ONNX model loaded: %s", self.model_path)
            except Exception as exc:  # pragma: no cover - env specific
                self._load_error = str(exc)
                log.warning("ONNX load failed, using fallback: %s", exc)
                self.session = None

    # ── public API ──────────────────────────────────────────────
    def classify(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"intent": "unknown", "score": 0.0, "source": "empty"}
        if self.session is not None and _HAS_NUMPY:
            try:
                return self._classify_onnx(text)
            except Exception as exc:  # pragma: no cover
                log.warning("ONNX infer failed, fallback: %s", exc)
        return self._classify_fallback(text)

    def health(self) -> Dict[str, Any]:
        return {
            "onnxruntime_available": _HAS_ORT,
            "numpy_available": _HAS_NUMPY,
            "model_loaded": self.session is not None,
            "model_path": str(self.model_path) if self.model_path else None,
            "load_error": self._load_error,
            "fallback_rules": len(_FALLBACK_RULES),
        }

    # ── internals ───────────────────────────────────────────────
    def _classify_onnx(self, text: str) -> Dict[str, Any]:
        # Expect a text input; real models vary. We feed the raw string
        # and read the first output tensor as logits over KNOWN_INTENTS.
        inp_name = self.session.get_inputs()[0].name
        feeds = {inp_name: np.array([text], dtype=object)}
        outs = self.session.run(None, feeds)
        logits = outs[0]
        if hasattr(logits, "tolist"):
            logits = logits.tolist()
        # flatten
        flat = logits[0] if isinstance(logits, list) else list(logits)
        idx = max(range(len(flat)), key=lambda i: flat[i])
        label = KNOWN_INTENTS[idx] if idx < len(KNOWN_INTENTS) else "unknown"
        score = float(flat[idx])
        return {"intent": label, "score": score, "source": "onnx"}

    def _classify_fallback(self, text: str) -> Dict[str, Any]:
        low = text.lower()
        for phrase, intent in _FALLBACK_RULES:
            if phrase in low:
                return {"intent": intent, "score": 1.0, "source": "keyword"}
        return {"intent": "unknown", "score": 0.0, "source": "keyword"}


def default_classifier(model_path: Optional[str] = None) -> OnnxIntentClassifier:
    """Factory honoring BROCCOLI_ONNX_MODEL env or an explicit path."""
    import os
    p = model_path or os.getenv("BROCCOLI_ONNX_MODEL")
    return OnnxIntentClassifier(Path(p) if p else None)
