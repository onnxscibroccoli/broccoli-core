"""Multi-provider chat history ingest adapters (M2).

Normalises exports from Grok, ChatGPT, Gemini, Claude, and generic web
AI chats into a single record shape the encrypted memory store + vector
index can consume. Each adapter is pure-Python and offline.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _base(provider: str, role: str, content: str, ts: Optional[float] = None, **extra) -> Dict[str, Any]:
    rec = {
        "provider": provider,
        "role": role,
        "content": content,
        "ts": ts,
    }
    rec.update(extra)
    return rec


class BaseAdapter:
    provider: str = "unknown"

    def parse(self, raw: Any) -> List[Dict[str, Any]]:
        raise NotImplementedError


class GrokAdapter(BaseAdapter):
    provider = "grok"

    def parse(self, raw: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except Exception:
                return [_base(self.provider, "user", raw)]
        items = raw if isinstance(raw, list) else raw.get("messages", raw.get("conversations", []))
        if not isinstance(items, list):
            return []
        for m in items:
            if not isinstance(m, dict):
                continue
            role = m.get("role") or m.get("author") or "user"
            content = m.get("content") or m.get("text") or ""
            if isinstance(content, list):
                content = " ".join(str(c) for c in content)
            out.append(_base(self.provider, str(role), str(content), m.get("ts") or m.get("timestamp")))
        return out


class ChatGPTAdapter(BaseAdapter):
    provider = "chatgpt"

    def parse(self, raw: Any) -> List[Dict[str, Any]]:
        # OpenAI export: conversations[].mapping -> messages
        out: List[Dict[str, Any]] = []
        convs = raw.get("conversations", [raw]) if isinstance(raw, dict) else raw
        if not isinstance(convs, list):
            return []
        for conv in convs:
            mapping = conv.get("mapping", {}) if isinstance(conv, dict) else {}
            for node in mapping.values():
                msg = node.get("message") if isinstance(node, dict) else None
                if not msg:
                    continue
                role = msg.get("author", {}).get("role", "user")
                content = msg.get("content", {})
                if isinstance(content, dict):
                    parts = content.get("parts", [])
                    text = " ".join(str(p) for p in parts)
                else:
                    text = str(content)
                out.append(_base(self.provider, role, text, msg.get("create_time")))
        return out


class GeminiAdapter(BaseAdapter):
    provider = "gemini"

    def parse(self, raw: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        items = raw if isinstance(raw, list) else [raw]
        for it in items:
            if not isinstance(it, dict):
                continue
            role = it.get("role") or ("user" if it.get("author") == "user" else "model")
            content = it.get("text") or it.get("content") or ""
            out.append(_base(self.provider, role, str(content), it.get("ts")))
        return out


class ClaudeAdapter(BaseAdapter):
    provider = "claude"

    def parse(self, raw: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        items = raw if isinstance(raw, list) else raw.get("messages", [raw])
        if not isinstance(items, list):
            return []
        for m in items:
            if not isinstance(m, dict):
                continue
            role = m.get("role") or "user"
            content = m.get("content")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c) for c in content
                )
            out.append(_base(self.provider, role, str(content), m.get("ts") or m.get("timestamp")))
        return out


class WebAIAdapter(BaseAdapter):
    """Generic scraper output: list of {role, text} dicts."""
    provider = "web"

    def parse(self, raw: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        items = raw if isinstance(raw, list) else [raw]
        for it in items:
            if not isinstance(it, dict):
                continue
            out.append(_base(self.provider, it.get("role", "user"), str(it.get("text", "")), it.get("ts")))
        return out


ADAPTERS: Dict[str, BaseAdapter] = {
    "grok": GrokAdapter(),
    "chatgpt": ChatGPTAdapter(),
    "gemini": GeminiAdapter(),
    "claude": ClaudeAdapter(),
    "web": WebAIAdapter(),
}


def ingest(provider: str, raw: Any) -> List[Dict[str, Any]]:
    ad = ADAPTERS.get(provider, WebAIAdapter())
    ad.provider = provider
    return ad.parse(raw)
