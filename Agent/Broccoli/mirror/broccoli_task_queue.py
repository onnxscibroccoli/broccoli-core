#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / "broccoli/lib"))
from task_queue import rebuild_context, enqueue, started, done, failed, note, log_event

def main():
    if len(sys.argv) < 2:
        print(rebuild_context())
        return 0
    a = sys.argv[1:]
    if a[0] in ("show", "context"):
        print(rebuild_context())
    elif a[0] == "paste":
        p = Path.home() / "broccoli/reports/task_queue_paste_block.txt"
        print(p.read_text(errors="replace") if p.exists() else rebuild_context())
    elif a[0] == "enqueue":
        enqueue(" ".join(a[1:]) or "unnamed")
        print("enqueued")
    elif a[0] == "log":
        log_event(a[1] if len(a) > 1 else "note", task=a[2] if len(a) > 2 else "", detail=" ".join(a[3:]))
        print("logged")
    else:
        print("broccoli_task_queue: show|paste|enqueue <task>|log <kind> <task> <detail>")
    return 0

if __name__ == "__main__":
    sys.exit(main())
