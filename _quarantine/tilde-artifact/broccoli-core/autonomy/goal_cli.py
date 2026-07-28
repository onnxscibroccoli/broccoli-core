#!/usr/bin/env python3
"""
Minimal Goal CLI for Broccoli Core autonomy layer.

Usage:
  python3 goal_cli.py list
  python3 goal_cli.py create "name" ["description"]
  python3 goal_cli.py status <goal_id>
  python3 goal_cli.py recover <goal_id>
  python3 goal_cli.py fail <goal_id> "reason"
  python3 goal_cli.py complete <goal_id>
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from event_bus import EventBus
from executor import Executor, GoalStatus

logging.basicConfig(level=logging.WARNING)  # quiet by default

bus = EventBus()
ex = Executor(event_bus=bus)

def cmd_list(_args):
    goals = ex.list_goals()
    if not goals:
        print("No goals.")
        return
    for g in sorted(goals, key=lambda x: x.created_at):
        status = g.status.name
        prog = f"{g.progress*100:.0f}%"
        retries = f" (retries {g.retry_count}/{g.max_retries})" if g.retry_count else ""
        print(f"{g.id[:8]}…  {status:<10} {prog:>4}  {g.name}{retries}")

def cmd_create(args):
    if not args:
        print("Usage: create <name> [description]")
        return
    name = args[0]
    desc = " ".join(args[1:]) if len(args) > 1 else ""
    g = ex.create_goal(name, desc)
    print(f"Created {g.id}")
    print(f"  name: {g.name}")

def cmd_status(args):
    if not args:
        print("Usage: status <goal_id_prefix>")
        return
    prefix = args[0]
    matches = [g for g in ex.list_goals() if g.id.startswith(prefix)]
    if not matches:
        print("No matching goal.")
        return
    g = matches[0]
    print(f"ID:          {g.id}")
    print(f"Name:        {g.name}")
    print(f"Status:      {g.status.name}")
    print(f"Progress:    {g.progress*100:.1f}%")
    print(f"Confidence:  {g.confidence:.2f}")
    print(f"Retries:     {g.retry_count}/{g.max_retries}")
    print(f"Checkpoints: {len(g.checkpoints)}")
    if g.error:
        print(f"Error:       {g.error}")
    if g.checkpoints:
        last = g.checkpoints[-1]
        print(f"Last CP:     step={last.step} data={last.data}")

def cmd_recover(args):
    if not args:
        print("Usage: recover <goal_id_prefix>")
        return
    prefix = args[0]
    matches = [g for g in ex.list_goals() if g.id.startswith(prefix)]
    if not matches:
        print("No matching goal.")
        return
    g = matches[0]
    ok = ex.recover_goal(g.id)
    print("Recovered." if ok else "Could not recover (max retries or wrong state).")

def cmd_fail(args):
    if len(args) < 2:
        print("Usage: fail <goal_id_prefix> <reason>")
        return
    prefix, reason = args[0], " ".join(args[1:])
    matches = [g for g in ex.list_goals() if g.id.startswith(prefix)]
    if not matches:
        print("No matching goal.")
        return
    ex.fail_goal(matches[0].id, reason)
    print("Marked FAILED.")

def cmd_complete(args):
    if not args:
        print("Usage: complete <goal_id_prefix>")
        return
    prefix = args[0]
    matches = [g for g in ex.list_goals() if g.id.startswith(prefix)]
    if not matches:
        print("No matching goal.")
        return
    ex.complete_goal(matches[0].id)
    print("Marked COMPLETED.")

COMMANDS = {
    "list": cmd_list,
    "create": cmd_create,
    "status": cmd_status,
    "recover": cmd_recover,
    "fail": cmd_fail,
    "complete": cmd_complete,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])
