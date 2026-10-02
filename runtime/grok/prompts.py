"""Prompt formatting for a Grok operator. Evidence only; no execution grant."""

from __future__ import annotations

import json
from typing import Any


def status_prompt(envelope: dict[str, Any]) -> str:
    sections = envelope.get("sections") or {}
    lines = [
        "BROCCOLI GROK STATUS",
        f"schema={envelope.get('schema_version')} correlation={envelope.get('correlation_id')}",
        f"collected_at={envelope.get('collected_at')}",
        f"execution_context={envelope.get('execution_context')}",
        "",
        "ROLE",
        "You are Broccoli's interactive development operator.",
        "Broccoli remains the deterministic execution and verification layer.",
        "Do not assume you may run commands. Propose; Broccoli verifies; the Governor authorizes.",
        "",
        "ENVIRONMENT",
        envelope.get("environment_note") or "",
        "",
    ]
    order = (
        "git",
        "runtime",
        "governor",
        "transports",
        "accessibility",
        "harvest",
        "errors",
        "tests",
        "objective",
    )
    for name in order:
        section = sections.get(name) or {}
        lines.append(name.upper())
        lines.append(f"ok={section.get('ok')} degraded={section.get('degraded')}")
        summary = section.get("summary")
        if summary:
            lines.append(str(summary))
        detail = section.get("detail")
        if detail:
            lines.append(json.dumps(detail, indent=2, sort_keys=True, default=str))
        lines.append("")
    lines.append("ASK")
    lines.append(
        "Summarize current state, name the single highest-confidence blocker, "
        "and recommend the next Broccoli-verifiable action. Do not invent file contents."
    )
    return "\n".join(lines).rstrip() + "\n"
