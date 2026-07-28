#!/usr/bin/env python3
"""Navigate chats — stub until sidebar list is verified in dump."""
def precondition(state: dict) -> tuple[bool, str]:
    if os.environ.get("BROCC_NAV_ALL") == "1":
        return False, "nav_all_not_implemented_verify_dump_first"
    return True, "current_only"

import os

def run(ctx) -> "ModuleResult":
    from modules.registry import ModuleResult
    # Phase 1: only current visible thread
    return ModuleResult(True, "chat_nav", data={"mode": "current_thread_only"})
