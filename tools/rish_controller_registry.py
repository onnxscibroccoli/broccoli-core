"""Fail-closed registry of controller apps allowed to drive the rish/Shizuku wire.

Only registered package ids may authorize, the rish side must run as uid 2000
(shell), and there is no default/fallback controller (Termux included).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REGISTRY = Path(__file__).resolve().with_name("rish_controllers.json")
SCHEMA = "broccoli.rish_controllers/v1"
SHELL_UID = 2000
ALLOWED_TRANSPORTS = frozenset({"rish_cli", "shizuku_userservice"})
_PKG_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")


class ControllerRefused(Exception):
    """Raised when a caller is not authorized for the rish wire."""


class RegistryInvalid(ControllerRefused):
    """Raised when the registry itself is malformed (fail closed)."""


@dataclass(frozen=True)
class Controller:
    package_id: str
    name: str
    rish_uid: int
    transport: str


def load_registry(path: Path | str | None = None) -> dict[str, Controller]:
    p = Path(path) if path is not None else DEFAULT_REGISTRY
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryInvalid(f"registry unreadable: {p.name}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise RegistryInvalid("registry schema mismatch")
    if data.get("required_rish_uid") != SHELL_UID:
        raise RegistryInvalid("registry required_rish_uid must be 2000")
    entries = data.get("controllers")
    if not isinstance(entries, list) or not entries:
        raise RegistryInvalid("registry has no controllers")
    out: dict[str, Controller] = {}
    for e in entries:
        if not isinstance(e, dict):
            raise RegistryInvalid("controller entry must be an object")
        pkg, uid, tr = e.get("package_id"), e.get("rish_uid"), e.get("transport")
        if not isinstance(pkg, str) or not _PKG_RE.match(pkg):
            raise RegistryInvalid(f"invalid package_id: {pkg!r}")
        if pkg in out:
            raise RegistryInvalid(f"duplicate package_id: {pkg}")
        if type(uid) is not int or uid != SHELL_UID:
            raise RegistryInvalid(f"{pkg}: rish_uid must be 2000")
        if tr not in ALLOWED_TRANSPORTS:
            raise RegistryInvalid(f"{pkg}: unknown transport {tr!r}")
        out[pkg] = Controller(pkg, str(e.get("name", pkg)), uid, tr)
    return out


def authorize(package_id, rish_uid, registry: dict[str, Controller] | None = None) -> Controller:
    """Return the Controller if (package_id, rish_uid) is allowed; else raise ControllerRefused."""
    reg = load_registry() if registry is None else registry
    if not isinstance(package_id, str) or not package_id:
        raise ControllerRefused("refused: caller package id missing (no default controller)")
    ctl = reg.get(package_id)
    if ctl is None:
        raise ControllerRefused(f"refused: controller {package_id!r} is not registered")
    if type(rish_uid) is not int or rish_uid != ctl.rish_uid:
        raise ControllerRefused(f"refused: {package_id} rish uid {rish_uid!r} != {ctl.rish_uid} (shell)")
    return ctl


if __name__ == "__main__":  # e.g. python3 tools/rish_controller_registry.py com.termux 2000
    import sys
    try:
        c = authorize(sys.argv[1] if len(sys.argv) > 1 else "", int(sys.argv[2]) if len(sys.argv) > 2 else -1)
    except (ControllerRefused, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(3)
    print(f"{c.package_id} {c.transport}")
