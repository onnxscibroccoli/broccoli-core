"""Deterministic evidence collection for `brocc grok status`.

Collectors never raise. Missing tools, Android shell restrictions, and absent
artifacts become degraded sections. Secrets are not copied into the envelope.
"""

from __future__ import annotations

import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|authorization|secret|password)\s*[:=]\s*\S+"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1=<redacted>", text)


def clip(text: str, limit: int = 2000) -> str:
    text = redact(text).strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…[truncated]"


def section(ok: bool, summary: str, detail: dict[str, Any] | None = None, degraded: bool = False) -> dict[str, Any]:
    return {
        "ok": ok,
        "degraded": degraded or not ok,
        "summary": summary,
        "detail": detail or {},
    }


def detect_context(env: dict[str, str] | None = None) -> dict[str, Any]:
    env = env if env is not None else dict(os.environ)
    home = env.get("HOME", "")
    termux = bool(env.get("TERMUX_VERSION") or env.get("PREFIX", "").find("com.termux") >= 0)
    rish = home == "/" or env.get("BROCC_SHELL") == "rish"
    if termux and not rish:
        name = "termux"
        note = (
            "Termux execution context. `brocc` belongs here. "
            "Do not expect `brocc` inside `rish`; that shell has HOME=/ "
            "and resolves $HOME/brocc to /brocc."
        )
    elif rish:
        name = "rish"
        note = (
            "Android/rish shell context. Privileged-by-Shizuku operations belong here. "
            "`brocc` is intentionally not on this PATH. ss/netlink permission errors "
            "are shell restrictions, not proof that networking is down."
        )
    else:
        name = "host"
        note = "Non-Termux host. Device collectors are skipped unless explicitly requested."
    return {"name": name, "termux": termux, "rish": rish, "home": home, "note": note}


def _run(cmd: list[str], cwd: Path, timeout: float = 5.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)
    text = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return proc.returncode, clip(text)


def collect_git(root: Path) -> dict[str, Any]:
    code, inside = _run(["git", "rev-parse", "--is-inside-work-tree"], root)
    if code != 0 or "true" not in inside:
        return section(False, "git metadata unavailable", {"error": inside or "not a work tree"})
    _, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)
    _, head = _run(["git", "rev-parse", "--short", "HEAD"], root)
    _, status = _run(["git", "status", "--short", "--branch"], root)
    _, last = _run(["git", "log", "-1", "--format=%h %s"], root)
    dirty = any(line and not line.startswith("##") for line in status.splitlines())
    return section(
        True,
        f"branch={branch.splitlines()[0] if branch else '?'} head={head.splitlines()[0] if head else '?'}",
        {"branch": branch, "head": head, "status": status, "last_commit": last, "dirty": dirty},
        degraded=dirty,
    )


def collect_runtime(root: Path) -> dict[str, Any]:
    pid_file = root / "runtime.pid"
    waiting = root / "WAITING_USER.txt"
    report = root / "reports" / "latest.txt"
    detail: dict[str, Any] = {
        "pid_file": pid_file.is_file(),
        "waiting_user": waiting.is_file(),
        "report_present": report.is_file(),
    }
    if report.is_file():
        detail["report_excerpt"] = clip(report.read_text(encoding="utf-8", errors="replace"), 800)
    ok = report.is_file() or pid_file.is_file()
    return section(ok, "runtime artifacts probed", detail, degraded=waiting.is_file() or not report.is_file())


def collect_governor(root: Path) -> dict[str, Any]:
    gov = root / "runtime" / "governor"
    present = gov.is_dir()
    names = sorted(p.name for p in gov.iterdir())[:20] if present else []
    return section(
        present,
        "governor package present" if present else "governor package missing",
        {"path": str(gov), "entries": names},
        degraded=not present,
    )


def collect_transports(root: Path, provider: bool) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "provider_probed": provider,
        "live_call": False,
        "note": "Phase 1 does not call Grok. Provider health is file-presence only.",
    }
    grok_py = root / "runtime" / "providers" / "grok.py"
    detail["grok_provider_module"] = grok_py.is_file()
    if provider:
        token_candidates = [
            Path.home() / ".broccoli" / "xai_oauth.json",
            root / ".xai_oauth.json",
        ]
        detail["oauth_files_present"] = [str(p) for p in token_candidates if p.is_file()]
    return section(grok_py.is_file(), "transport modules probed; no live call", detail, degraded=not provider)


def collect_accessibility(root: Path, probe_device: bool) -> dict[str, Any]:
    if not probe_device:
        return section(
            True,
            "accessibility not probed (no --device)",
            {"probed": False},
            degraded=True,
        )
    code, text = _run(["sh", "-c", "command -v dumpsys >/dev/null && dumpsys accessibility | head -n 40"], root, timeout=8)
    return section(code == 0, "dumpsys accessibility" if code == 0 else "dumpsys unavailable", {"output": text})


def collect_harvest(root: Path) -> dict[str, Any]:
    harvest = root / "data" / "harvest"
    if not harvest.is_dir():
        return section(False, "no data/harvest directory", {"path": str(harvest)})
    files = [p for p in harvest.rglob("*") if p.is_file()]
    if not files:
        return section(False, "harvest directory empty", {"path": str(harvest)})
    latest = max(files, key=lambda p: p.stat().st_mtime)
    return section(
        True,
        f"latest harvest {latest.name}",
        {
            "path": str(latest),
            "bytes": latest.stat().st_size,
            "excerpt": clip(latest.read_text(encoding="utf-8", errors="replace"), 600),
        },
    )


def collect_errors(root: Path) -> dict[str, Any]:
    candidates = [root / "error.log", root / "broccoli.log", root / "logs" / "broccoli.log"]
    hits: list[str] = []
    for path in candidates:
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:]
        except OSError:
            continue
        for line in lines:
            if re.search(r"(?i)error|traceback|exception", line):
                hits.append(f"{path.name}: {clip(line, 240)}")
    hits = hits[-12:]
    return section(
        True,
        f"{len(hits)} recent error-like lines" if hits else "no recent error-like lines in known logs",
        {"lines": hits},
        degraded=bool(hits),
    )


def collect_tests(root: Path, run_tests: bool) -> dict[str, Any]:
    result = root / "self_test_results.txt"
    detail: dict[str, Any] = {"recorded_result": result.is_file(), "ran": False}
    if result.is_file():
        detail["excerpt"] = clip(result.read_text(encoding="utf-8", errors="replace"), 800)
    if run_tests:
        code, text = _run(["python3", "-m", "unittest", "runtime.grok.tests.test_status"], root, timeout=60)
        detail["ran"] = True
        detail["exit_code"] = code
        detail["output"] = text
        return section(code == 0, "grok status unit tests executed", detail, degraded=code != 0)
    return section(True, "tests not executed (pass --run-tests)", detail, degraded=not result.is_file())


def collect_objective(root: Path) -> dict[str, Any]:
    candidates = [root / "current_task.txt", root / "prompts" / "next_prompt.md", root / "HANDOFF.md"]
    found = []
    for path in candidates:
        if path.is_file():
            found.append({"path": str(path), "excerpt": clip(path.read_text(encoding="utf-8", errors="replace"), 500)})
    return section(bool(found), "objective files probed", {"files": found}, degraded=not found)


def collect(
    root: Path,
    *,
    provider: bool = False,
    probe_device: bool = False,
    run_tests: bool = False,
    env: dict[str, str] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    context = detect_context(env)
    collectors: dict[str, Callable[[], dict[str, Any]]] = {
        "git": lambda: collect_git(root),
        "runtime": lambda: collect_runtime(root),
        "governor": lambda: collect_governor(root),
        "transports": lambda: collect_transports(root, provider),
        "accessibility": lambda: collect_accessibility(root, probe_device),
        "harvest": lambda: collect_harvest(root),
        "errors": lambda: collect_errors(root),
        "tests": lambda: collect_tests(root, run_tests),
        "objective": lambda: collect_objective(root),
    }
    sections: dict[str, Any] = {}
    for name, fn in collectors.items():
        try:
            sections[name] = fn()
        except Exception as exc:  # noqa: BLE001 — collector boundary
            sections[name] = section(False, "collector failed", {"error": type(exc).__name__})
    return {
        "schema_version": 1,
        "kind": "grok.status",
        "correlation_id": correlation_id or uuid.uuid4().hex[:12],
        "collected_at": utc_now(),
        "root": str(root),
        "execution_context": context["name"],
        "environment_note": context["note"],
        "authority": {
            "grok_may_execute": False,
            "governor_required_for_consequential_actions": True,
        },
        "sections": sections,
    }
