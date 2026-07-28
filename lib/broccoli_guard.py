"""Central guard: no self-mutation of core .py/.sh when BROCC_NO_SELF_MUTATE=1."""
import fnmatch
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PERMS = ROOT / "broccoli_permissions.json"

def _load():
    if PERMS.exists():
        return json.loads(PERMS.read_text(encoding="utf-8"))
    return {}

def no_self_mutate() -> bool:
    return os.environ.get("BROCC_NO_SELF_MUTATE", "1") != "0"

def blocked_write(path: str | Path) -> bool:
    if not no_self_mutate():
        return False
    p = Path(path).resolve()
    try:
        rel = p.relative_to(ROOT)
    except ValueError:
        return False
    s = str(rel).replace("\\", "/")
    data = _load()
    for g in data.get("block_write_globs", []):
        if fnmatch.fnmatch(s, g) or fnmatch.fnmatch(p.name, g):
            return True
    if s.endswith(".py") and "quarantine" not in s and "archive" not in s:
        # default: block any .py write outside allow list
        allowed = False
        for g in data.get("allow_write_globs", []):
            if fnmatch.fnmatch(s, g):
                allowed = True
                break
        if not allowed:
            return True
    return False

def assert_may_write(path: str | Path):
    if blocked_write(path):
        raise PermissionError(f"BROCC guard blocked write: {path}")

def may_run_quarry() -> bool:
    return os.environ.get("BROCC_NO_SELF_MUTATE", "1") == "0"
