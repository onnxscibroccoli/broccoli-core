#!/usr/bin/env python3
"""After task complete: toast for next task; remind every 60s until user_next_task.txt is set."""
import json, time
from pathlib import Path

ROOT = Path.home() / "broccoli"
META, UI = ROOT / "meta", ROOT / "ui"

def cfg():
    p = META / "iter_loop.json"
    return json.loads(p.read_text()) if p.exists() else {}

def toast(msg, long=False):
    import subprocess
    cmd = ["termux-toast", "-g", "center", msg[:120]]
    if long:
        cmd = ["termux-toast", "-g", "center", "-s", "long", msg[:200]]
    subprocess.run(cmd, timeout=8, capture_output=True)
    print("TOAST", msg, flush=True)

def notify(msg):
    import subprocess
    subprocess.run([
        "termux-notification", "--title", "Broccoli",
        "--content", msg[:200], "--priority", "high", "--id", "broccoli_need_task",
    ], timeout=8, capture_output=True)

def user_task_ready():
    p = UI / "user_next_task.txt"
    if not p.exists():
        return False, ""
    t = p.read_text(errors="replace").strip()
    if not t or t.startswith("#"):
        return False, ""
    return True, t

def wait_for_user_task():
    c = cfg()
    interval = int(c.get("need_task_toast_interval_sec", 60))
    poll = int(c.get("wait_poll_sec", 5))
    task_file = Path(c.get("user_task_file", str(UI / "user_next_task.txt")))

    toast("Task complete. Send next task → user_next_task.txt", long=True)
    notify("Task done. Add next task in ~/broccoli/ui/user_next_task.txt")

    last_toast = 0
    while True:
        ok, task = user_task_ready()
        if ok:
            toast(f"Got task: {task[:50]}…")
            # consume: move to iter_prompt and clear wait file
            (UI / "iter_prompt.txt").write_text(task, encoding="utf-8")
            (UI / "loop_inbox.txt").write_text(task, encoding="utf-8")
            consumed = UI / "user_next_task.consumed"
            consumed.write_text(task, encoding="utf-8")
            task_file.write_text("", encoding="utf-8")
            return task

        now = time.time()
        if now - last_toast >= interval:
            toast("Broccoli needs a task (edit ui/user_next_task.txt)", long=True)
            notify("Broccoli needs a task — ui/user_next_task.txt")
            last_toast = now

        time.sleep(poll)

if __name__ == "__main__":
    t = wait_for_user_task()
    print("TASK", t)
