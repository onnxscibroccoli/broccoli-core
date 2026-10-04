"""Deterministic evidence envelope for brocc grok status.

Collectors never raise into the caller. Missing tools, Android shell
restrictions, and absent artifacts become explicit degraded sections.
"""

from __future__ import annotations

import os
import platform
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

SCHEMA_VERSION = "broccoli.grok.evidence.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def repo_root() -> Path:
    env = os.environ.get("BROCC_ROOT")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parents[2]


def execution_context() -> Dict[str, Any]:
    """Distinguish Termux (brocc home) from rish/Android shell.

    rish sets HOME to / and does not inherit the Termux PATH. brocc must
    stay a Termux command; privileged probes are optional and separate.
    """
    home = os.environ.get("HOME", "")
    prefix = os.environ.get("PREFIX", "")
    termux = bool(prefix.startswith("/data/data/com.termux")) or "com.termux" in os.environ.get("PATH", "")
    rish_like = home in {"/", ""} and not termux
    return {
        "home": home or None,
        "prefix": prefix or None,
        "termux": termux,
        "rish_like": rish_like,
        "platform": platform.system(),
        "note": (
            "brocc belongs to Termux. Do not expect $HOME/brocc inside rish."
            if rish_like
            else "Termux or host execution context."
        ),
    }


def _run(cmd: List[str], cwd: Optional[Path] = None, timeout: float = 4.0) -> Dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return {"ok": False, "error": f"missing:{exc.filename}", "stdout": "", "stderr": ""}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "stdout": "", "stderr": ""}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}
    return {
        "ok": proc.returncode == 0,
        "code": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
    }


def _section(name: str, fn: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
    try:
        payload = fn()
        status = payload.pop("_status", "ok")
        return {"name": name, "status": status, "data": payload}
    except Exception as exc:  # noqa: BLE001 — collectors must degrade
        return {"name": name, "status": "error", "data": {"error": f"{type(exc).__name__}: {exc}"}}


def collect_git(root: Path) -> Dict[str, Any]:
    if not (root / ".git").exists():
        return {"_status": "degraded", "present": False, "reason": "no .git"}
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root)
    head = _run(["git", "rev-parse", "--short", "HEAD"], cwd=root)
    status = _run(["git", "status", "--porcelain"], cwd=root)
    log = _run(["git", "log", "-1", "--format=%s"], cwd=root)
    if not branch["ok"]:
        return {"_status": "degraded", "present": True, "error": branch.get("stderr") or branch.get("error")}
    dirty = [line for line in status.get("stdout", "").splitlines() if line][:40]
    return {
        "present": True,
        "branch": branch["stdout"],
        "head": head.get("stdout"),
        "subject": log.get("stdout"),
        "dirty_count": len(status.get("stdout", "").splitlines()) if status.get("stdout") else 0,
        "dirty": dirty,
    }


def collect_runtime(root: Path) -> Dict[str, Any]:
    markers = [
        "runtime/kernel.py",
        "runtime/prod.py",
        "runtime/governor",
        "runtime/transports",
        "bin/brocc",
    ]
    present = {rel: (root / rel).exists() for rel in markers}
    waiting = (root / "WAITING_USER.txt").exists()
    return {
        "_status": "ok" if present.get("runtime/prod.py") else "degraded",
        "markers": present,
        "waiting_user": waiting,
    }


def collect_governor(root: Path) -> Dict[str, Any]:
    gov = root / "runtime" / "governor"
    transports = root / "runtime" / "transports"
    return {
        "_status": "ok" if gov.is_dir() else "degraded",
        "governor_present": gov.is_dir(),
        "transports_present": transports.is_dir(),
        "booted": False,
        "note": "status does not boot governor or transports",
    }


def collect_accessibility(root: Path) -> Dict[str, Any]:
    script = root / "runtime" / "accessibility_orchestration.sh"
    dumpsys = _run(["dumpsys", "accessibility"], timeout=2.0)
    if dumpsys["ok"]:
        text = dumpsys["stdout"]
        enabled = "enabled services" in text.lower() or "Accessibility services" in text
        return {
            "script_present": script.exists(),
            "dumpsys": "available",
            "snippet": text[:400],
            "likely_enabled": enabled,
        }
    return {
        "_status": "degraded",
        "script_present": script.exists(),
        "dumpsys": "unavailable",
        "reason": dumpsys.get("error") or dumpsys.get("stderr") or "not an Android shell",
        "note": "ss/netlink permission errors inside rish are shell restrictions, not proof networking is down",
    }


def _newest(paths: List[Path]) -> Optional[Path]:
    existing = [p for p in paths if p.is_file()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def collect_harvest(root: Path) -> Dict[str, Any]:
    harvest_dir = root / "data" / "harvest"
    report = root / "reports" / "latest.txt"
    files = list(harvest_dir.glob("*.jsonl")) if harvest_dir.is_dir() else []
    newest = _newest(files)
    payload: Dict[str, Any] = {
        "dir_present": harvest_dir.is_dir(),
        "file_count": len(files),
        "report_present": report.is_file(),
    }
    if newest:
        payload["newest"] = str(newest.relative_to(root))
        payload["newest_mtime"] = datetime.fromtimestamp(newest.stat().st_mtime, timezone.utc).isoformat()
    if report.is_file():
        text = report.read_text(encoding="utf-8", errors="replace")
        payload["report_tail"] = text[-800:]
    if not newest and not report.is_file():
        payload["_status"] = "degraded"
        payload["reason"] = "no harvest files or reports/latest.txt"
    return payload


def collect_errors(root: Path) -> Dict[str, Any]:
    candidates = [
        root / "logs" / "broccoli.log",
        root / "logs" / "worker.log",
        root / "broccoli.log",
    ]
    log = next((p for p in candidates if p.is_file()), None)
    if not log:
        return {"_status": "degraded", "present": False, "reason": "no canonical log"}
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
    hits = [ln for ln in lines if any(tok in ln.lower() for tok in ("error", "traceback", "exception", "failed"))]
    return {"present": True, "path": str(log.relative_to(root)), "recent_hits": hits[-12:]}


def collect_tests(root: Path) -> Dict[str, Any]:
    artifacts = [
        root / "data" / "grok" / "last_test.json",
        root / "reports" / "pytest.txt",
    ]
    found = next((p for p in artifacts if p.is_file()), None)
    if not found:
        return {
            "_status": "degraded",
            "ran": False,
            "reason": "status does not execute the suite; no last-test artifact",
        }
    text = found.read_text(encoding="utf-8", errors="replace")
    return {"ran": False, "artifact": str(found.relative_to(root)), "tail": text[-500:]}


def collect_objective(root: Path) -> Dict[str, Any]:
    candidates = [
        root / "prompts" / "next_prompt.md",
        root / "state" / "objective.txt",
        root / "WAITING_USER.txt",
    ]
    found = next((p for p in candidates if p.is_file()), None)
    if not found:
        return {"_status": "degraded", "present": False, "reason": "no objective file"}
    text = found.read_text(encoding="utf-8", errors="replace").strip()
    return {"present": True, "path": str(found.relative_to(root)), "text": text[:1200]}


def collect_evidence(root: Optional[Path] = None) -> Dict[str, Any]:
    root = (root or repo_root()).resolve()
    sections = [
        _section("git", lambda: collect_git(root)),
        _section("runtime", lambda: collect_runtime(root)),
        _section("governor_transport", lambda: collect_governor(root)),
        _section("accessibility", lambda: collect_accessibility(root)),
        _section("harvest", lambda: collect_harvest(root)),
        _section("errors", lambda: collect_errors(root)),
        _section("tests", lambda: collect_tests(root)),
        _section("objective", lambda: collect_objective(root)),
    ]
    degraded = [s["name"] for s in sections if s["status"] != "ok"]
    return {
        "schema": SCHEMA_VERSION,
        "correlation_id": correlation_id(),
        "timestamp": utc_now(),
        "root": str(root),
        "execution": execution_context(),
        "authority": {
            "grok_may_execute": False,
            "governor_required_for_consequential_actions": True,
            "collection_only": True,
        },
        "sections": sections,
        "degraded": degraded,
    }
