"""Pick a VirtualSurface implementation.

Prefers OnDevice tools/rish_display.py when present and compatible.
Never imports provider package names. Falls back to MemorySurface.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from runtime.surface.memory import MemorySurface


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_rish_module() -> Any:
    path = _repo_root() / "tools" / "rish_display.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("broccoli_ondemand_rish_display", path)
    if spec is None or spec.loader is None:
        return None
    mod = importlib.util.module_from_spec(spec)
    # dataclasses and other runtime type helpers resolve cls.__module__ through
    # sys.modules while the module is executing. Register before exec_module.
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return mod


def open_surface(session: str = "ready"):
    try:
        mod = _load_rish_module()
    except Exception:
        mod = None
    if mod is not None:
        for name in ("RishSurface", "VirtualSurface", "Surface", "Display"):
            cls = getattr(mod, name, None)
            if cls is None:
                continue
            try:
                inst = cls()
            except Exception:
                continue
            if all(hasattr(inst, m) for m in ("create", "inspect", "input", "submit")):
                return inst, "rish"
            return inst, "rish_partial"
    return MemorySurface(session=session), "memory"
