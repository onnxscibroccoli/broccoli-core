"""Client for the Cloudflare broccoli-edge Worker.

Talks to BROCCOLI_EDGE_URL for hash embeddings and intent classification.
Falls back to pure on-device logic when the edge is unreachable — the
offline path never dies. No secrets, no commercial gate.
"""
from __future__ import annotations

import os
import json
import urllib.request
from typing import Any, Dict, List, Optional


class EdgeClient:
    def __init__(self, base_url: Optional[str] = None, timeout: float = 8.0) -> None:
        self.base_url = (base_url or os.getenv("BROCCOLI_EDGE_URL") or "").rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.base_url:
            return None
        try:
            req = urllib.request.Request(
                self.base_url + path,
                data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def embed(self, text: str) -> Optional[List[float]]:
        r = self._post("/embed", {"text": text})
        if r and r.get("ok"):
            return r.get("vector")
        return None

    def infer(self, text: str) -> Dict[str, Any]:
        r = self._post("/infer", {"text": text})
        if r and r.get("ok"):
            return {"intent": r.get("intent", "unknown"), "confidence": r.get("confidence", 0.0), "source": "edge"}
        # offline fallback — same keyword logic, local
        t = (text or "").lower()
        if "bluetooth" in t or " bt" in t:
            return {"intent": "toggle_bluetooth", "confidence": 0.7, "source": "local"}
        if "remind" in t:
            return {"intent": "set_reminder", "confidence": 0.7, "source": "local"}
        if "calendar" in t or "schedule" in t:
            return {"intent": "open_calendar", "confidence": 0.7, "source": "local"}
        return {"intent": "unknown", "confidence": 0.0, "source": "local"}

    def health(self) -> Dict[str, Any]:
        if not self.base_url:
            return {"configured": False, "ready": False}
        try:
            with urllib.request.urlopen(self.base_url + "/health", timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
            return {"configured": True, "ready": bool(data.get("ok")), "service": data.get("service")}
        except Exception as exc:
            return {"configured": True, "ready": False, "error": str(exc)}
