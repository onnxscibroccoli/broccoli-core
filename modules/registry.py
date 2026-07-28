"""Module registry — name, precondition, run."""
from dataclasses import dataclass
from typing import Callable, Any, Optional

@dataclass
class ModuleResult:
    ok: bool
    name: str
    reason: str = ""
    data: Optional[dict] = None

@dataclass
class Ctx:
    root: str
    state: dict
    env: dict

def gate(pre: Callable[[dict], tuple[bool, str]], state: dict, name: str) -> Optional[str]:
    ok, reason = pre(state)
    if not ok:
        return f"{name}:blocked:{reason}"
    return None
