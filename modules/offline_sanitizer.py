"""Tokenize user fields before any sync operation."""
from __future__ import annotations
import hashlib
import json
import re
from typing import Any, Dict

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"\+?\d[\d\s\-()]{7,}\d")

def _token(label: str, value: str) -> str:
    h = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"tok_{label}_{h}"

def sanitize_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: sanitize_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_obj(v) for v in obj]
    if isinstance(obj, str):
        s = obj
        s = EMAIL.sub(lambda m: _token("email", m.group(0)), s)
        s = PHONE.sub(lambda m: _token("phone", m.group(0)), s)
        return s
    return obj

def sanitize_json_text(text: str) -> str:
    return json.dumps(sanitize_obj(json.loads(text)), separators=(",", ":"))
