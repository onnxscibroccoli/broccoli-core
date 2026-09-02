"""Encrypted offline memory store (M1).

Fernet-encrypted JSON records on disk. No network, no cloud, no
commercial gate. The key lives in BROCCOLI_MEMORY_KEY (env) or a local
file with mode 600. Designed for brain-injury recovery: every
conversation, automation, and sensor reading the user opts into gets
stored here, searchable later by the vector index.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from cryptography.fernet import Fernet  # type: ignore
    _HAS_FERNET = True
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore
    _HAS_FERNET = False

DEFAULT_DB = Path.home() / ".broccoli" / "memory.db"
DEFAULT_KEY_FILE = Path.home() / ".broccoli" / "memory.key"


class EncryptedMemoryStore:
    """Append-only encrypted record store."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        key: Optional[bytes] = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = self._make_fernet(key)
        self._records: List[Dict[str, Any]] = self._load()

    # ── crypto ──────────────────────────────────────────────────
    def _make_fernet(self, key: Optional[bytes]):
        if not _HAS_FERNET:
            return None
        if key is None:
            key = self._load_or_create_key()
        if isinstance(key, str):
            key = key.encode()
        return Fernet(key)

    def _load_or_create_key(self) -> bytes:
        env = os.getenv("BROCCOLI_MEMORY_KEY")
        if env:
            return env.encode() if isinstance(env, str) else env
        if DEFAULT_KEY_FILE.is_file():
            return DEFAULT_KEY_FILE.read_bytes().strip()
        if not _HAS_FERNET:
            return b""
        k = Fernet.generate_key()
        DEFAULT_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_KEY_FILE.write_bytes(k)
        try:
            os.chmod(DEFAULT_KEY_FILE, 0o600)
        except Exception:
            pass
        return k

    # ── persistence ─────────────────────────────────────────────
    def _load(self) -> List[Dict[str, Any]]:
        if not self.db_path.is_file() or self._fernet is None:
            return []
        try:
            raw = self.db_path.read_bytes()
            if not raw:
                return []
            plain = self._fernet.decrypt(raw)
            data = json.loads(plain.decode())
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self) -> None:
        if self._fernet is None:
            self.db_path.write_text(json.dumps(self._records, indent=2))
            return
        token = self._fernet.encrypt(json.dumps(self._records).encode())
        self.db_path.write_bytes(token)
        try:
            os.chmod(self.db_path, 0o600)
        except Exception:
            pass

    # ── public API ──────────────────────────────────────────────
    def add(self, record: Dict[str, Any]) -> str:
        rec = dict(record)
        rec.setdefault("ts", time.time())
        rec.setdefault("id", f"{int(rec['ts']*1000)}")
        self._records.append(rec)
        self._save()
        return rec["id"]

    def all(self) -> List[Dict[str, Any]]:
        return list(self._records)

    def search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        q = (query or "").lower()
        if not q:
            return self._records[:limit]
        hits = []
        for r in self._records:
            blob = json.dumps(r).lower()
            if q in blob:
                hits.append(r)
                if len(hits) >= limit:
                    break
        return hits

    def health(self) -> Dict[str, Any]:
        return {
            "fernet_available": _HAS_FERNET,
            "records": len(self._records),
            "db_path": str(self.db_path),
            "encrypted": self._fernet is not None,
        }
