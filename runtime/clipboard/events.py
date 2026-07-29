from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

CLIPBOARD_COMMAND_RECEIVED = "CLIPBOARD_COMMAND_RECEIVED"
CLIPBOARD_COMMAND_RESULT = "CLIPBOARD_COMMAND_RESULT"
CLIPBOARD_AGENT_RESULT_PREFIX = "[Clipboard Agent Result]"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def command_id_for(command: str) -> str:
    normalized = command.strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_result_envelope(text: str) -> bool:
    return text.lstrip().startswith(CLIPBOARD_AGENT_RESULT_PREFIX)


def parse_result_envelope(text: str) -> Dict[str, Any]:
    result_time: Optional[str] = None
    command_lines: list[str] = []
    output_lines: list[str] = []
    mode: Optional[str] = None

    for line in text.splitlines():
        stripped = line.strip()

        if stripped == CLIPBOARD_AGENT_RESULT_PREFIX:
            continue
        if stripped.startswith("Time:"):
            result_time = stripped.split("Time:", 1)[1].strip()
            continue
        if stripped == "Command:":
            mode = "command"
            continue
        if stripped == "Output:":
            mode = "output"
            continue

        if mode == "command":
            command_lines.append(line)
        elif mode == "output":
            output_lines.append(line)

    command = "\n".join(command_lines).strip()
    output = "\n".join(output_lines).strip()

    return {
        "result_time": result_time,
        "command": command,
        "output": output,
        "raw": text,
    }


def build_command_payload(text: str, source: str = "clipboard.bridge") -> Dict[str, Any]:
    command = text.strip()
    command_id = command_id_for(command)

    return {
        "command_id": command_id,
        "command": command,
        "clipboard": text,
        "clipboard_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "captured_at": utc_now_iso(),
        "source": source,
        "kind": "command",
    }


def build_result_payload(text: str, source: str = "clipboard.bridge") -> Dict[str, Any]:
    parsed = parse_result_envelope(text)
    command = parsed["command"]
    command_id = command_id_for(command) if command else hashlib.sha256(text.encode("utf-8")).hexdigest()

    return {
        "command_id": command_id,
        "command": command,
        "output": parsed["output"],
        "result_time": parsed["result_time"],
        "clipboard": text,
        "clipboard_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "captured_at": utc_now_iso(),
        "source": source,
        "kind": "result",
    }
