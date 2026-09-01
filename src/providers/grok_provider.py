"""GrokProvider — OAuth-first, API-key fallback.

Prefers an active XaiOAuthProvider session. Only falls back to XAI_API_KEY
when no OAuth token is present, and only with a loud warning.
"""
from __future__ import annotations

import os
import warnings
from typing import Any, Optional

from .xai_oauth import XaiOAuthProvider


class GrokProvider:
    def __init__(self, oauth: Optional[XaiOAuthProvider] = None) -> None:
        self.oauth = oauth or XaiOAuthProvider()
        self._warned = False

    def _auth_header(self) -> str:
        if self.oauth.has_session():
            return f"Bearer {self.oauth.get_access_token()}"
        key = os.environ.get("XAI_API_KEY")
        if not key:
            raise RuntimeError(
                "No OAuth session and no XAI_API_KEY. "
                "Run `broccoli xai login` or set XAI_API_KEY."
            )
        if not self._warned:
            warnings.warn(
                "Using XAI_API_KEY fallback. Prefer OAuth: `broccoli xai login`. "
                "API keys bill separately from your SuperGrok subscription.",
                stacklevel=2,
            )
            self._warned = True
        return f"Bearer {key}"

    def chat(self, messages: list[dict[str, str]], model: str = "grok-4.6", **kw: Any) -> dict[str, Any]:
        import json
        import urllib.request

        payload = {"model": model, "messages": messages, "temperature": kw.get("temperature", 0)}
        req = urllib.request.Request(
            "https://api.x.ai/v1/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": self._auth_header(),
            },
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
