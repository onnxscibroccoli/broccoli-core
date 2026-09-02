"""Shared Fernet key load/create. Mode 600. Optional dependency."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet  # type: ignore

    HAS_FERNET = True
except Exception:  # pragma: no cover
    Fernet = None  # type: ignore
    HAS_FERNET = False

DEFAULT_KEY_FILE = Path.home() / ".broccoli" / "memory.key"


def key_file_path() -> Path:
    override = os.environ.get("BROCCOLI_MEMORY_KEY_FILE", "").strip()
    if override:
        return Path(override)
    return DEFAULT_KEY_FILE


def load_or_create_key(path: Optional[Path] = None) -> Optional[bytes]:
    env = os.environ.get("BROCCOLI_MEMORY_KEY", "").strip()
    if env:
        return env.encode()
    if not HAS_FERNET:
        return None
    target = Path(path) if path else key_file_path()
    if target.is_file():
        raw = target.read_bytes().strip()
        return raw if raw else None
    key = Fernet.generate_key()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(key)
    try:
        os.chmod(target, 0o600)
    except OSError:
        pass
    return key


def make_fernet(key: Optional[bytes] = None, key_file: Optional[Path] = None):
    if not HAS_FERNET:
        return None
    material = key
    if material is None:
        material = load_or_create_key(key_file)
    if material is None:
        return None
    if isinstance(material, str):
        material = material.encode()
    try:
        return Fernet(material)
    except Exception:
        return None
