"""Cloudflare free-tier client. Disabled until creds exist. Never blocks the phone."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass
class EdgeConfig:
    account_id: str = field(default_factory=lambda: os.getenv("CF_ACCOUNT_ID", ""))
    api_token: str = field(default_factory=lambda: os.getenv("CF_API_TOKEN", ""))
    worker_url: str = field(default_factory=lambda: os.getenv("CF_WORKER_URL", ""))
    kv_namespace: str = field(default_factory=lambda: os.getenv("CF_KV_NAMESPACE", ""))

    @property
    def enabled(self) -> bool:
        return bool(self.worker_url or (self.account_id and self.api_token))


class CloudflareEdge:
    def __init__(self, cfg: Optional[EdgeConfig] = None) -> None:
        self.cfg = cfg or EdgeConfig()

    def health(self) -> Tuple[bool, Dict[str, Any]]:
        if not self.cfg.enabled:
            return False, {"reason": "unconfigured", "enabled": False}
        return True, {"enabled": True, "worker": bool(self.cfg.worker_url)}

    def kv_get(self, key: str) -> Tuple[bool, Dict[str, Any]]:
        if not self.cfg.enabled:
            return False, {"error": "unconfigured", "key": key}
        return False, {"error": "offline_stub", "key": key}

    def kv_put(self, key: str, value: str) -> Tuple[bool, Dict[str, Any]]:
        if not self.cfg.enabled:
            return False, {"error": "unconfigured"}
        return False, {"error": "offline_stub"}

    def d1_rate_limited(self) -> bool:
        """D1 daily write cap is real as of 2026-09-01. Callers must check this."""
        return False

    def embed(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        if not self.cfg.enabled:
            return False, {"error": "unconfigured"}
        return False, {"error": "offline_stub"}
