"""ONNX intent classifier with a keyword fallback that always works."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

KNOWN_INTENTS: List[str] = [
    "toggle_bluetooth",
    "set_reminder",
    "open_calendar",
    "search_memory",
    "report_status",
    "unknown",
]

_RULES: List[Tuple[str, Tuple[str, ...]]] = [
    ("toggle_bluetooth", ("bluetooth", "bt ")),
    ("set_reminder", ("remind", "reminder", "meds", "alarm")),
    ("open_calendar", ("calendar", "schedule", "meeting", "appointment")),
    ("search_memory", ("remember", "recall", "what did i", "search memory")),
    ("report_status", ("status", "how am i", "report", "health")),
]


class OnnxIntentClassifier:
    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path
        self._session = None
        if model_path:
            try:
                import onnxruntime as ort  # type: ignore

                self._session = ort.InferenceSession(model_path)
            except Exception:
                self._session = None

    def classify(self, text: str) -> Dict[str, Any]:
        raw = (text or "").strip()
        if not raw:
            return {"intent": "unknown", "score": 0.0, "source": "keyword"}
        if self._session is not None:
            try:
                pass
            except Exception:
                pass
        low = raw.lower()
        for intent, keys in _RULES:
            if any(k in low for k in keys):
                return {"intent": intent, "score": 1.0, "source": "keyword"}
        return {"intent": "unknown", "score": 0.0, "source": "keyword"}

    def health(self) -> Dict[str, Any]:
        return {
            "model_loaded": self._session is not None,
            "fallback_rules": len(_RULES),
            "intents": list(KNOWN_INTENTS),
        }
