from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from runtime.eventbus import EventBus
from runtime.providers.base import Provider


class GrokProvider(Provider):
    """Real xAI Grok provider.

    Talks to https://api.x.ai/v1/chat/completions with a real API key.
    No more print-and-pray. Results are published on the EventBus so the
    Governor, agents, and any subscriber can act on them.
    """

    DEFAULT_BASE_URL = "https://api.x.ai/v1"
    DEFAULT_MODEL = "grok-4.6"

    def __init__(
        self,
        bus: EventBus,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ) -> None:
        self.bus = bus
        self.api_key = api_key or os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        self.base_url = (base_url or os.getenv("XAI_API_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("GROK_MODEL") or self.DEFAULT_MODEL
        self.timeout = timeout
        self.initialized = False
        self.session_active = False
        self._last_error: Optional[str] = None
        self._last_latency_ms: Optional[float] = None
        self._request_count = 0

    # ------------------------------------------------------------------ lifecycle
    def initialize(self) -> bool:
        if not self.api_key:
            self._last_error = "missing XAI_API_KEY / GROK_API_KEY"
            self.bus.publish(
                "ProviderError",
                {"provider": "grok", "error": self._last_error},
                source="GrokProvider",
            )
            return False
        self.initialized = True
        self.session_active = True
        self._last_error = None
        self.bus.publish("ProviderConnected", "grok", source="GrokProvider")
        return True

    def shutdown(self) -> bool:
        self.session_active = False
        self.bus.publish("ProviderDisconnected", "grok", source="GrokProvider")
        return True

    # ------------------------------------------------------------------ transport
    def send(self, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Send a chat completion and publish the real result."""
        if not self.session_active:
            self.initialize()
        if not self.session_active:
            return False

        messages = self._build_messages(message, context)
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
        }
        started = time.monotonic()
        try:
            raw = self._post("/chat/completions", payload)
            self._last_latency_ms = (time.monotonic() - started) * 1000.0
            self._request_count += 1
            self._last_error = None
        except Exception as exc:  # pragma: no cover - network path
            self._last_error = str(exc)
            self._last_latency_ms = (time.monotonic() - started) * 1000.0
            self.bus.publish(
                "ProviderError",
                {"provider": "grok", "error": self._last_error, "context": context},
                source="GrokProvider",
            )
            return False

        content = self._extract_content(raw)
        result = {
            "provider": "grok",
            "model": self.model,
            "request": message,
            "response": content,
            "raw": raw,
            "latency_ms": self._last_latency_ms,
            "context": context or {},
        }
        self.bus.publish("ConversationUpdated", result, source="GrokProvider")
        self.bus.publish("ProviderResult", result, source="GrokProvider")
        return True

    def stream(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Streaming is not wired yet; fall back to a single send."""
        ok = self.send(message, context)
        if ok:
            # Re-publish as a stream chunk so existing subscribers keep working.
            self.bus.publish(
                "StreamChunk",
                {"provider": "grok", "chunk": message, "context": context or {}},
                source="GrokProvider",
            )
        return ok

    # ------------------------------------------------------------------ health
    def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self.session_active and not self._last_error else "degraded",
            "provider": "grok",
            "model": self.model,
            "session": self.session_active,
            "requests": self._request_count,
            "latency_ms": self._last_latency_ms,
            "last_error": self._last_error,
            "has_key": bool(self.api_key),
        }

    def capabilities(self) -> Dict[str, bool]:
        return {"chat": True, "vision": True, "tools": True, "streaming": False}

    # ------------------------------------------------------------------ internals
    def _build_messages(
        self, message: str, context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    "You are Broccoli Core's Grok provider. "
                    "Answer concisely. Return structured JSON when asked."
                ),
            }
        ]
        if context:
            ctx = context.get("system") or context.get("system_prompt")
            if ctx:
                messages[0]["content"] = str(ctx)
            history = context.get("history") or []
            for turn in history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant", "system") and content:
                    messages.append({"role": role, "content": str(content)})
        messages.append({"role": "user", "content": message})
        return messages

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "broccoli-core/grok-provider",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"xAI HTTP {exc.code}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"xAI network error: {exc.reason}") from exc

    @staticmethod
    def _extract_content(raw: Dict[str, Any]) -> str:
        try:
            return raw["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return ""
