from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """Tiny, file-backed config.

    Reads runtime/config.json (or $BROCCOLI_CONFIG) and overlays env vars.
    Keeps secrets out of git: only non-secret defaults live here.
    """

    DEFAULT_PATH = Path.home() / "broccoli" / "config.json"

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else Path(
            os.getenv("BROCCOLI_CONFIG", self.DEFAULT_PATH)
        )
        self.tick_seconds = 2.0
        self.max_workers = 4
        self.log_level = "INFO"
        self.grok_model = os.getenv("GROK_MODEL", "grok-4.6")
        self.xai_base_url = os.getenv("XAI_API_BASE_URL", "https://api.x.ai/v1")
        self._raw: Dict[str, Any] = {}

    def load(self) -> "Config":
        if self.path.is_file():
            try:
                self._raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._raw = {}
        for key in ("tick_seconds", "max_workers", "log_level", "grok_model", "xai_base_url"):
            if key in self._raw:
                setattr(self, key, self._raw[key])
        return self

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "tick_seconds": self.tick_seconds,
            "max_workers": self.max_workers,
            "log_level": self.log_level,
            "grok_model": self.grok_model,
            "xai_base_url": self.xai_base_url,
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)
