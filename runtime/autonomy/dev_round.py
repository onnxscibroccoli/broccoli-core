"""Confirmation-gated autonomy rounds + GitHub-synced goals."""
from __future__ import annotations
import json, subprocess, time
from pathlib import Path
from typing import Any, Dict

ROOT = Path.home() / "broccoli-core"
META = ROOT / "meta" / "always_on"
NOTES = META / "notes"
OUTBOX = META / "outbox"
HANDOFF = ROOT / "meta" / "handoff"

def _read(p: Path, default: str = "") -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else default
    except Exception:
        return default

def sync_github() -> Dict[str, Any]:
    HANDOFF.mkdir(parents=True, exist_ok=True)
    info: Dict[str, Any] = {}
    try:
        info["branch"] = subprocess.check_output(["git","branch","--show-current"], cwd=str(ROOT), text=True).strip()
        info["head"] = subprocess.check_output(["git","rev-parse","--short","HEAD"], cwd=str(ROOT), text=True).strip()
    except Exception as e:
        info["git_error"] = str(e)
    try:
        with open(HANDOFF / "open_issues.txt", "w") as f:
            subprocess.run(["gh","issue","list","--state","open","--limit","30"], cwd=str(ROOT), stdout=f, stderr=subprocess.DEVNULL)
    except Exception:
        pass
    info["issues_text"] = _read(HANDOFF / "open_issues.txt")[:3000]
    (HANDOFF / "github_sync.json").write_text(json.dumps(info, indent=2))
    return info

def propose_goal() -> Dict[str, Any]:
    META.mkdir(parents=True, exist_ok=True)
    gh = sync_github()
    goals = [
        {"id":"G1","priority":1,"title":"Grok inject + continuous autonomy rounds",
         "detail":"Open ai.x.grok, inject context packet, send via Speak/up-arrow-right-of-mic","issue":12},
        {"id":"G2","priority":2,"title":"AIM_UI_DUMP send path validated",
         "detail":"composer=chat_text_input; send=Speak then up-arrow right of mic","issue":12},
        {"id":"G3","priority":3,"title":"GitHub-tracked seamless development",
         "detail":"commit/push alpha-testing + comment issue #12 each milestone","issue":12},
        {"id":"G4","priority":4,"title":"Smoke truth residual",
         "detail":"Issue #2 residual: e2e smoke reflects real state","issue":2},
    ]
    proposed = {
        "timestamp": int(time.time()),
        "status": "proposed",
        "branch": gh.get("branch"),
        "head": gh.get("head"),
        "observed_goal": (
            "Primary: validate Grok FG open + context inject + send (up-arrow right of mic) "
            "for confirmed autonomy rounds; track all work on issue #12."
        ),
        "goals": goals,
        "open_issues": gh.get("issues_text","")[:1500],
        "research_notes": [
            "Package ai.x.grok",
            "Composer chat_text_input",
            "Send: Speak empty; up-arrow ImageButton right of mic with text",
            "Dump only when packages include ai.x.grok",
        ],
        "confirmed_via": None,
    }
    (META / "goal_proposed.json").write_text(json.dumps(proposed, indent=2))
    return proposed

def confirm_goal(source: str = "chat") -> Dict[str, Any]:
    if not (META / "goal_proposed.json").is_file():
        propose_goal()
    data = json.loads(_read(META / "goal_proposed.json", "{}"))
    data["status"] = "confirmed"
    data["confirmed_via"] = source
    data["confirmed_at"] = int(time.time())
    (META / "goal_active.json").write_text(json.dumps(data, indent=2))
    (META / "goal_confirmed").write_text(f"confirmed via {source}\n")
    return data

def is_confirmed() -> bool:
    return (META / "goal_confirmed").is_file() and (META / "goal_active.json").is_file()

def build_context_packet() -> Path:
    META.mkdir(parents=True, exist_ok=True)
    active = json.loads(_read(META / "goal_active.json", "{}") or "{}")
    goal = active.get("observed_goal") or "unspecified"
    goals = active.get("goals") or []
    goals_txt = "\n".join(f"- [{g.get('id')}] {g.get('title')}: {g.get('detail')}" for g in goals)
    notes = []
    NOTES.mkdir(parents=True, exist_ok=True)
    for p in sorted(NOTES.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
        notes.append(f"- {p.name}: {_read(p)[:180].replace(chr(10),' ')}")
    packet = f"""# Broccoli Core autonomy context

## Confirmed goal
{goal}

## Goal backlog
{goals_txt or '- (none)'}

## UI research
- ai.x.grok | composer chat_text_input | send Speak then up-arrow right of mic

## Open issues
{_read(HANDOFF/'open_issues.txt')[:800]}

## Recent notes
{chr(10).join(notes) or '- (none)'}

## Round rules
1. Stay on this chat when possible.
2. Smallest next implementation step only.
3. End with DONE / BLOCKED / NEXT.
"""
    path = META / "context_packet.md"
    path.write_text(packet)
    return path

def run_round(task: str = "", force: bool = False) -> Dict[str, Any]:
    if not force and not is_confirmed():
        return {"ok": False, "need_confirm": True, "proposed": propose_goal()}
    packet = build_context_packet().read_text()
    active = json.loads(_read(META / "goal_active.json", "{}") or "{}")
    goal = active.get("observed_goal") or "continue"
    body = packet + "\n\n## This round\n" + (task or f"Advance: {goal}")
    OUTBOX.mkdir(parents=True, exist_ok=True)
    out = OUTBOX / f"{int(time.time())}_dev_round.txt"
    out.write_text(body)
    (META / "auto_reply.enabled").write_text("1\n")
    from runtime.autonomy.chat_assist import run_once
    result = run_once(app_key="grok", open_if_needed=True, auto_reply=True)
    NOTES.mkdir(parents=True, exist_ok=True)
    ts = int(time.time())
    note = {"timestamp": ts, "goal": goal, "task": task, "fg": result.get("foreground_package"),
            "send": result.get("send"), "ui": result.get("ui")}
    (NOTES / f"round_{ts}.json").write_text(json.dumps(note, indent=2))
    (NOTES / f"round_{ts}.md").write_text(f"# Round {ts}\n\nGoal: {goal}\n\nTask: {task}\n\nFG: {note['fg']}\n")
    return {"ok": True, "note": f"meta/always_on/notes/round_{ts}.json", "result": result}

def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("cmd", nargs="?", default="status",
                   choices=["sync","propose","confirm","status","packet","round"])
    p.add_argument("--task", default="")
    p.add_argument("--source", default="chat")
    p.add_argument("--force", action="store_true")
    args = p.parse_args()
    if args.cmd == "sync":
        print(json.dumps(sync_github(), indent=2))
    elif args.cmd == "propose":
        print(json.dumps(propose_goal(), indent=2))
    elif args.cmd == "confirm":
        print(json.dumps(confirm_goal(source=args.source), indent=2))
    elif args.cmd == "status":
        print(json.dumps({"confirmed": is_confirmed(),
                          "proposed": (META/"goal_proposed.json").is_file(),
                          "active": (META/"goal_active.json").is_file()}, indent=2))
    elif args.cmd == "packet":
        print(str(build_context_packet()))
    else:
        print(json.dumps(run_round(task=args.task, force=args.force), indent=2, default=str))

if __name__ == "__main__":
    main()
