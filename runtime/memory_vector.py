"""Encrypted append-only memory. Mode 600. Searchable. Offline."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.crypto_key import HAS_FERNET as _HAS_FERNET
from runtime.crypto_key import make_fernet


@dataclass
class MemoryHit:
    text: str
    kind: str
    source: str
    ts: float
    meta: Dict[str, Any]


class EncryptedMemory:
    def __init__(self, path: Path | str, key: Optional[bytes] = None) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = make_fernet(key)
        self._rows: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.path.is_file():
            return []
        raw = self.path.read_bytes()
        if not raw:
            return []
        try:
            if self._fernet is not None:
                raw = self._fernet.decrypt(raw)
            data = json.loads(raw.decode())
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self) -> None:
        blob = json.dumps(self._rows).encode()
        if self._fernet is not None:
            blob = self._fernet.encrypt(blob)
        self.path.write_bytes(blob)
        try:
            os.chmod(self.path, 0o600)
        except Exception:
            pass

    def remember(
        self,
        text: str,
        kind: str = "note",
        source: str = "broccoli",
        **meta: Any,
    ) -> str:
        rec = {
            "text": text,
            "kind": kind,
            "source": source,
            "ts": time.time(),
            "meta": meta,
        }
        self._rows.append(rec)
        self._save()
        return str(rec["ts"])

    def search(self, query: str, limit: int = 20) -> List[MemoryHit]:
        q = (query or "").lower()
        hits: List[MemoryHit] = []
        for r in self._rows:
            blob = json.dumps(r).lower()
            if not q or q in blob:
                hits.append(
                    MemoryHit(
                        text=str(r.get("text", "")),
                        kind=str(r.get("kind", "")),
                        source=str(r.get("source", "")),
                        ts=float(r.get("ts") or 0),
                        meta=dict(r.get("meta") or {}),
                    )
                )
                if len(hits) >= limit:
                    break
        return hits
