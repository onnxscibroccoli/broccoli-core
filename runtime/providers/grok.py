"""Real xAI Grok provider with OAuth-first auth.

Prefers a SuperGrok OAuth session (runtime.providers.xai_oauth) and only
falls back to XAI_API_KEY with a loud warning that it's a separate metered
ledger. Results are published on the EventBus.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.eventbus import EventBus
from runtime.providers.base import Provider
from runtime.providers import xai_oauth as xo


class GrokProvider(Provider):
    """Real xAI Grok provider. OAuth session first, API key fallback."""

    DEFAULT_BASE_URL = "https://api.x.ai/v1"
    DEFAULT_MODEL = "grok-4.6"

    def __init__(
        self,
        bus: EventBus,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
        token_path: Optional[str] = None,
    ) -> None:
        self.bus = bus
        self.api_key = api_key or os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        self.base_url = (base_url or os.getenv("XAI_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("GROK_MODEL") or self.DEFAULT_MODEL
        self.timeout = timeout
        self.token_path = Path(token_path) if token_path else xo.DEFAULT_TOKEN_PATH
        self.initialized = False
        self.session_active = False
        self._auth_mode: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_latency_ms: Optional[float] = None
        self._request_count = 0

    def initialize(self) -> bool:
        token = xo.get_access_token(self.token_path)
        if token:
            self._auth_mode = "oauth"
            self.initialized = True
            self.session_active = True
            self._last_error = None
            self.bus.publish("ProviderConnected", {"provider": "grok", "auth": "oauth"}, source="GrokProvider")
            return True
        if self.api_key:
            self._auth_mode = "api_key"
            self.initialized = True
            self.session_active = True
            self._last_error = None
            self.bus.publish(
                "ProviderConnected",
                {"provider": "grok", "auth": "api_key", "warning": "metered API key — separate ledger from SuperGrok"},
                source="GrokProvider",
            )
            return True
        self._last_error = "no OAuth session and no XAI_API_KEY — run: python -m runtime.providers.xai_oauth login"
        self.bus.publish("ProviderError", {"provider": "grok", "error": self._last_error}, source="GrokProvider")
        return False

    def shutdown(self) -> bool:
        self.session_active = False
        self.bus.publish("ProviderDisconnected", "grok", source="GrokProvider")
        return True

    def send(self, message: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if not self.session_active:
            self.initialize()
        if not self.session_active:
            return False

        messages = self._build_messages(message, context)
        payload = {"model": self.model, "messages": messages, "temperature": 0.2}
        started = time.monotonic()
        try:
            raw = self._post("/chat/completions", payload)
            self._last_latency_ms = (time.monotonic() - started) * 1000.0
            self._request_count += 1
            self._last_error = None
        except Exception as exc:
            self._last_error = str(exc)
            self._last_latency_ms = (time.monotonic() - started) * 1000.0
            self.bus.publish(
                "ProviderError",
                {"provider": "grok", "error": self._last_error, "context": context, "auth": self._auth_mode},
                source="GrokProvider",
            )
            return False

        content = self._extract_content(raw)
        result = {
            "provider": "grok",
            "model": self.model,
            "auth": self._auth_mode,
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
        ok = self.send(message, context)
        if ok:
            self.bus.publish(
                "StreamChunk",
                {"provider": "grok", "chunk": message, "context": context or {}},
                source="GrokProvider",
            )
        return ok

    def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self.session_active and not self._last_error else "degraded",
            "provider": "grok",
            "model": self.model,
            "auth": self._auth_mode,
            "session": self.session_active,
            "requests": self._request_count,
            "latency_ms": self._last_latency_ms,
            "last_error": self._last_error,
            "has_oauth": bool(xo.get_access_token(self.token_path)),
            "has_key": bool(self.api_key),
        }

    def capabilities(self) -> Dict[str, bool]:
        return {"chat": True, "vision": True, "tools": True, "streaming": False, "oauth": True}

    def _build_messages(self, message: str, context: Optional[Dict[str, Any]]) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = [{
            "role": "system",
            "content": "You are Broccoli Core's Grok provider. Answer concisely. Return structured JSON when asked.",
        }]
        if context:
            ctx = context.get("system") or context.get("system_prompt")
            if ctx:
                messages[0]["content"] = str(ctx)
            for turn in context.get("history") or []:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant", "system") and content:
                    messages.append({"role": role, "content": str(content)})
        messages.append({"role": "user", "content": message})
        return messages

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        token = xo.get_access_token(self.token_path) if self._auth_mode == "oauth" else self.api_key
        if not token:
            raise RuntimeError("no auth token available")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
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
