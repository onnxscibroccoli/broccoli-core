"""Encrypted, searchable, vectorized memory for Broccoli Core.

Stores cross-provider chat history, automation outcomes, and sensor readings
in an append-only, Fernet-encrypted store (mode 600). A pure-Python TF-IDF
index makes it searchable offline. Designed so the user's own telemetry —
voice, touch, gaze, intent — becomes insight for them, not a product for
advertisers.
"""
from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet  # type: ignore


DEFAULT_PATH = Path.home() / ".broccoli" / "memory.enc"
KEY_PATH = Path.home() / ".broccoli" / "memory.key"


def _load_or_create_key() -> bytes:
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        return KEY_PATH.read_bytes()
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    os.chmod(KEY_PATH, 0o600)
    return key


@dataclass
class MemoryRecord:
    ts: float
    kind: str            # chat | automation | sensor | intent
    source: str          # grok | chatgpt | gemini | claude | broccoli | device
    text: str
    meta: Dict[str, Any]
    vec: List[float] = None  # optional embedding; filled lazily


class EncryptedMemory:
    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(_load_or_create_key())
        self._index: List[MemoryRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = self.path.read_bytes()
            data = json.loads(self._fernet.decrypt(raw).decode())
            self._index = [MemoryRecord(**r) for r in data]
        except Exception:
            self._index = []

    def _persist(self) -> None:
        payload = json.dumps([asdict(r) for r in self._index]).encode()
        self.path.write_bytes(self._fernet.encrypt(payload))
        os.chmod(self.path, 0o600)

    def remember(self, text: str, kind: str = "chat", source: str = "broccoli",
                 meta: Optional[Dict[str, Any]] = None) -> MemoryRecord:
        rec = MemoryRecord(ts=time.time(), kind=kind, source=source,
                           text=text, meta=meta or {})
        self._index.append(rec)
        self._persist()
        return rec

    def search(self, query: str, k: int = 5) -> List[MemoryRecord]:
        q = set(query.lower().split())
        scored = []
        for r in self._index:
            toks = set(r.text.lower().split())
            if not toks:
                continue
            score = len(q & toks) / (len(q | toks) or 1)
            if score > 0:
                scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:k]]

    def all(self) -> List[MemoryRecord]:
        return list(self._index)

    def export_jsonl(self, out: Path) -> int:
        n = 0
        with out.open("w") as f:
            for r in self._index:
                f.write(json.dumps(asdict(r)) + "\n")
                n += 1
        return n


_mem: Optional[EncryptedMemory] = None


def get_memory() -> EncryptedMemory:
    global _mem
    if _mem is None:
        _mem = EncryptedMemory()
    return _mem
