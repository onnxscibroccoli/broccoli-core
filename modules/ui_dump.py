#!/usr/bin/env python3
import os, subprocess
from modules.state_probe import snap, read_dump, ROOT

def precondition(state: dict) -> tuple[bool, str]:
    if not state.get("in_grok_chat"):
        return False, "not_in_grok"
    return True, "ok"

def run(ctx) -> "ModuleResult":
    from modules.registry import ModuleResult
    snap()
    xml = read_dump()
    path = os.path.join(ctx.root, "ui", "last_window_dump.xml")
    open(path, "w", encoding="utf-8", errors="ignore").write(xml)
    return ModuleResult(True, "ui_dump", data={"path": path, "len": len(xml)})
