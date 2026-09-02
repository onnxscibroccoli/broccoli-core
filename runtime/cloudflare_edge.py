"""Cloudflare free-tier edge client for Broccoli Core.

Maps the free resource surface so Broccoli can offload work without a credit
card:
  - Workers: 100k req/day, 50 subrequests/req, 128MB mem, 10ms CPU (free)
  - KV: 100k reads/day, 1k writes/day, 1GB, 25MiB/value
  - D1: 5M row reads/day, 100k writes/day, 5GB (NOTE: daily limits now
        enforced as of 2026-09-01; degrade gracefully on limit errors)
  - R2: 10GB, 1M Class A / 10M Class B ops/month, free egress forever
  - Workers AI: 10,000 Neurons/day shared across models
  - Vectorize: 30M query dims/month, 5M storage dims (free)

Design rule: every call is best-effort. If the edge is unreachable or rate-
limited, the caller falls back to on-device / local execution. Never block
the user's intent on a remote dependency.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests


CF_API = "https://api.cloudflare.com/client/v4"


@dataclass
class EdgeConfig:
    account_id: str = ""
    api_token: str = ""          # CF_API_TOKEN
    kv_namespace: str = ""
    d1_database: str = ""
    r2_bucket: str = ""
    worker_url: str = ""         # deployed worker endpoint
    ai_model: str = "@cf/qwen/qwen1.5-0.5b-chat"

    @classmethod
    def from_env(cls) -> "EdgeConfig":
        return cls(
            account_id=os.environ.get("CF_ACCOUNT_ID", ""),
            api_token=os.environ.get("CF_API_TOKEN", ""),
            kv_namespace=os.environ.get("CF_KV_NAMESPACE", ""),
            d1_database=os.environ.get("CF_D1_DATABASE", ""),
            r2_bucket=os.environ.get("CF_R2_BUCKET", ""),
            worker_url=os.environ.get("CF_WORKER_URL", ""),
            ai_model=os.environ.get("CF_AI_MODEL", "@cf/qwen/qwen1.5-0.5b-chat"),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.api_token and self.account_id)


class CloudflareEdge:
    """Thin, resilient client. Every method returns (ok, data_or_error)."""
    def __init__(self, cfg: Optional[EdgeConfig] = None) -> None:
        self.cfg = cfg or EdgeConfig.from_env()
        self._session = requests.Session()
        if self.cfg.api_token:
            self._session.headers.update({"Authorization": f"Bearer {self.cfg.api_token}"})

    # -- health ----------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        if not self.cfg.enabled:
            return {"enabled": False, "reason": "no CF_API_TOKEN/CF_ACCOUNT_ID"}
        try:
            r = self._session.get(f"{CF_API}/accounts/{self.cfg.account_id}", timeout=8)
            return {"enabled": True, "status": r.status_code, "ok": r.ok}
        except Exception as e:  # noqa: BLE001
            return {"enabled": True, "ok": False, "error": str(e)}

    # -- KV --------------------------------------------------------------------
    def kv_get(self, key: str) -> tuple[bool, Any]:
        if not (self.cfg.kv_namespace and self.cfg.enabled):
            return False, "kv not configured"
        url = (f"{CF_API}/accounts/{self.cfg.account_id}/storage/kv/namespaces/"
               f"{self.cfg.kv_namespace}/values/{key}")
        try:
            r = self._session.get(url, timeout=8)
            if r.status_code == 404:
                return True, None
            if r.ok:
                return True, r.text
            return False, r.text
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    def kv_put(self, key: str, value: str) -> tuple[bool, Any]:
        if not (self.cfg.kv_namespace and self.cfg.enabled):
            return False, "kv not configured"
        url = (f"{CF_API}/accounts/{self.cfg.account_id}/storage/kv/namespaces/"
               f"{self.cfg.kv_namespace}/values/{key}")
        try:
            r = self._session.put(url, data=value.encode(), timeout=8)
            return r.ok, r.text if not r.ok else "ok"
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    # -- D1 (graceful on daily-limit errors) -----------------------------------
    def d1_query(self, sql: str, params: Optional[list] = None) -> tuple[bool, Any]:
        if not (self.cfg.d1_database and self.cfg.enabled):
            return False, "d1 not configured"
        url = (f"{CF_API}/accounts/{self.cfg.account_id}/d1/database/"
               f"{self.cfg.d1_database}/query")
        body = {"sql": sql, "params": params or []}
        try:
            r = self._session.post(url, json=body, timeout=15)
            if r.status_code in (429, 503):
                return False, "d1_rate_limited"
            data = r.json()
            if not r.ok:
                return False, data
            return True, data.get("result", [])
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    # -- R2 -------------------------------------------------------------------
    def r2_put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> tuple[bool, Any]:
        if not (self.cfg.r2_bucket and self.cfg.enabled):
            return False, "r2 not configured"
        url = (f"{CF_API}/accounts/{self.cfg.account_id}/r2/buckets/"
               f"{self.cfg.r2_bucket}/objects/{key}")
        try:
            r = self._session.put(url, data=data,
                                  headers={"Content-Type": content_type}, timeout=30)
            return r.ok, r.text if not r.ok else "ok"
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    # -- Workers AI ------------------------------------------------------------
    def ai_infer(self, prompt: str, model: Optional[str] = None) -> tuple[bool, Any]:
        if not self.cfg.enabled:
            return False, "ai not configured"
        model = model or self.cfg.ai_model
        url = f"{CF_API}/accounts/{self.cfg.account_id}/ai/run/{model}"
        try:
            r = self._session.post(url, json={"prompt": prompt}, timeout=30)
            if r.status_code in (429, 503):
                return False, "ai_rate_limited"
            return r.ok, r.json() if r.ok else r.text
        except Exception as e:  # noqa: BLE001
            return False, str(e)

    # -- Worker endpoint (custom) ---------------------------------------------
    def worker_post(self, path: str, payload: Dict[str, Any]) -> tuple[bool, Any]:
        if not self.cfg.worker_url:
            return False, "no worker url"
        try:
            r = self._session.post(f"{self.cfg.worker_url.rstrip('/')}/{path.lstrip('/')}",
                                   json=payload, timeout=20)
            return r.ok, r.json() if r.ok else r.text
        except Exception as e:  # noqa: BLE001
            return False, str(e)


_edge: Optional[CloudflareEdge] = None


def get_edge() -> CloudflareEdge:
    global _edge
    if _edge is None:
        _edge = CloudflareEdge()
    return _edge
