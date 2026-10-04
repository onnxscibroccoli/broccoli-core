"""Compact prompt rendering for a Grok evidence envelope."""

from __future__ import annotations

from typing import Any, Dict


def render_prompt(envelope: Dict[str, Any]) -> str:
    lines = [
        "BROCCOLI EVIDENCE PACKET",
        f"schema: {envelope.get('schema')}",
        f"correlation_id: {envelope.get('correlation_id')}",
        f"timestamp: {envelope.get('timestamp')}",
        f"root: {envelope.get('root')}",
        "",
        "AUTHORITY",
        "Grok may propose. Broccoli verifies. Governor authorizes consequential actions.",
        "This packet is collection-only.",
        "",
        "EXECUTION CONTEXT",
    ]
    execution = envelope.get("execution") or {}
    lines.append(
        f"termux={execution.get('termux')} rish_like={execution.get('rish_like')} home={execution.get('home')}"
    )
    lines.append(str(execution.get("note") or ""))
    lines.append("")
    for section in envelope.get("sections") or []:
        lines.append(f"## {section.get('name')} [{section.get('status')}]")
        data = section.get("data") or {}
        for key, value in data.items():
            text = str(value).replace("\n", " | ")
            if len(text) > 500:
                text = text[:500] + "..."
            lines.append(f"- {key}: {text}")
        lines.append("")
    degraded = envelope.get("degraded") or []
    lines.append("DEGRADED: " + (", ".join(degraded) if degraded else "none"))
    lines.append("Ask for diagnosis only. Do not assume missing sections are failures.")
    return "\n".join(lines).rstrip() + "\n"
