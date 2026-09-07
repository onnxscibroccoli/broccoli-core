"""CLI: python -m runtime.watchme <cmd>"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from runtime.watchme.catalog import WatchCatalog
from runtime.watchme.record import WatchSession

_STATE = Path.home() / ".broccoli" / "watchme" / "session.json"


def _load_session() -> WatchSession:
    if not _STATE.exists():
        raise SystemExit("no open watch session; start <title> first")
    raw = json.loads(_STATE.read_text(encoding="utf-8"))
    ses = WatchSession(raw["title"], raw.get("requested_by", "user"))
    ses.id = raw["id"]
    ses.started_at = raw["started_at"]
    ses.steps = list(raw.get("steps") or [])
    return ses


def _save_session(ses: WatchSession) -> None:
    _STATE.parent.mkdir(parents=True, exist_ok=True)
    _STATE.write_text(
        json.dumps(
            {
                "id": ses.id,
                "title": ses.title,
                "requested_by": ses.requested_by,
                "started_at": ses.started_at,
                "steps": ses.steps,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cat = WatchCatalog()
    if not argv or argv[0] in ("help", "-h", "--help"):
        print(
            "watchme start <title>\n"
            "watchme step <action> [text] [--role r]\n"
            "watchme stop [--no-authorize]\n"
            "watchme list|search <q>|run <id>|ingest-demo"
        )
        return 0
    cmd = argv[0]
    if cmd == "start":
        title = " ".join(argv[1:]) or "untitled"
        ses = WatchSession(title)
        _save_session(ses)
        print(json.dumps({"ok": True, "id": ses.id, "title": ses.title}))
        return 0
    if cmd == "step":
        ses = _load_session()
        action = argv[1] if len(argv) > 1 else "observe"
        role = ""
        rest = argv[2:]
        if "--role" in rest:
            i = rest.index("--role")
            role = rest[i + 1] if i + 1 < len(rest) else ""
            del rest[i : i + 2]
        text = " ".join(rest)
        print(json.dumps(ses.record(action, role=role, text=text)))
        _save_session(ses)
        return 0
    if cmd == "stop":
        ses = _load_session()
        authorize = "--no-authorize" not in argv
        demo = ses.finish(authorize=authorize)
        cat.save(demo)
        _STATE.unlink(missing_ok=True)
        print(json.dumps({"ok": True, "saved": demo["id"], "authorized": demo["authorized"], "steps": len(demo["steps"])}))
        return 0
    if cmd == "list":
        print(json.dumps(cat.search(""), indent=2))
        return 0
    if cmd == "search":
        print(json.dumps(cat.search(" ".join(argv[1:])), indent=2))
        return 0
    if cmd == "run":
        if len(argv) < 2:
            print("run <id>", file=sys.stderr)
            return 2
        print(json.dumps(cat.replay(argv[1]), indent=2))
        return 0
    if cmd == "ingest-demo":
        demo = cat.record_and_save(
            "example: open notes and type hello",
            [
                {"action": "tap", "role": "notes", "text": "Notes"},
                {"action": "focus", "role": "composer", "text": ""},
                {"action": "input", "role": "composer", "text": "hello"},
                {"action": "submit", "role": "send", "text": ""},
            ],
            authorize=True,
        )
        print(json.dumps({"ok": True, "id": demo["id"], "title": demo["title"]}))
        return 0
    print("unknown command", cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
