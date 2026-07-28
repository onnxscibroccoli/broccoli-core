#!/usr/bin/env python3
"""
Automate operator steps: set task, clip status, stop/start agent, health.
No manual brocc stop / tee / clipboard / echo next task (use set-next-task).
"""
import json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path.home() / "broccoli"
LIB, META, UI, REP = ROOT / "lib", ROOT / "meta", ROOT / "ui", ROOT / "reports"
sys.path.insert(0, str(LIB))

PIDF = REP / "agent_loop.pid"
LOGF = REP / "agent_live.log"

def toast(msg, long=False):
    cmd = ["termux-toast", "-g", "center", msg[:120]]
    if long:
        cmd = ["termux-toast", "-g", "center", "-s", "long", msg[:200]]
    subprocess.run(cmd, timeout=8, capture_output=True)

def clip_file(path):
    p = Path(path)
    if not p.exists():
        return False
    subprocess.run([sys.executable, str(LIB / "clip.py")], input=p.read_bytes(),
                   timeout=15, capture_output=True)
    return True

def clip_text(s):
    subprocess.run([sys.executable, str(LIB / "clip.py")], input=s.encode("utf-8"),
                   timeout=15, capture_output=True)

def agent_running():
    if not PIDF.exists():
        return False
    try:
        pid = int(PIDF.read_text().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False

def stop_agent():
    subprocess.run([sys.executable, str(ROOT / "broccoli_stop.py")], timeout=60, capture_output=True)
    if PIDF.exists():
        try:
            os.kill(int(PIDF.read_text().strip()), 15)
        except Exception:
            pass
        PIDF.unlink(missing_ok=True)

def start_agent():
    stop_agent()
    REP.mkdir(parents=True, exist_ok=True)
    with open(LOGF, "ab", buffering=0) as log:
        p = subprocess.Popen(
            [sys.executable, str(LIB / "agent_loop.py")],
            stdout=log, stderr=subprocess.STDOUT,
            cwd=str(ROOT),
        )
    PIDF.write_text(str(p.pid))
    toast("Agent loop started (auto)", long=True)
    return p.pid

def set_current_task(task_id, title, body=None):
    body = body or title
    now = time.time()
    cur = {
        "task_id": task_id,
        "task": title,
        "status": "running",
        "started_at": now,
        "started_human": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
        "detail": body[:2000],
        "round": 1,
        "history": [],
    }
    META.mkdir(parents=True, exist_ok=True)
    (META / "current_task.json").write_text(json.dumps(cur, indent=2))
    (META / "current_task.md").write_text(f"# {title}\n\n{body}\n")
    UI.mkdir(parents=True, exist_ok=True)
    (UI / "iter_prompt.txt").write_text(body)
    (UI / "loop_inbox.txt").write_text(body)
    try:
        from task_queue import enqueue, started, note, rebuild_context
        enqueue(task_id, detail=title)
        started(task_id, detail="operator set")
        note(f"CURRENT TASK SET: {title}")
        rebuild_context()
    except Exception:
        pass

def set_next_task(line):
    line = (line or "").strip()
    if not line or line.startswith("#"):
        toast("Empty task", long=True)
        return
    (UI / "user_next_task.txt").write_text(line + "\n")
    toast(f"Next task queued: {line[:40]}…")

def status_bundle():
    parts = []
    for p in (META / "current_task.md", META / "current_task.json", ROOT / "broccoli_task_queue.py"):
        if p.name.endswith(".py"):
            r = subprocess.run([sys.executable, str(p), "show"], capture_output=True, text=True, timeout=30)
            parts.append(r.stdout or r.stderr)
        elif p.exists():
            parts.append(p.read_text(errors="replace"))
    parts.append(f"agent_running={agent_running()} pid={PIDF.read_text().strip() if PIDF.exists() else 'none'}")
    return "\n---\n".join(parts)

def cmd_autopilot():
    """Default: ensure current task, clip status, start agent if not running."""
    if not (META / "current_task.json").exists():
        set_current_task(
            "broccoli_agent_loop_v1",
            "Broccoli continuous agent loop (UI-driven completion)",
            (UI / "iter_prompt.txt").read_text(errors="replace") if (UI / "iter_prompt.txt").exists() else "Run agent loop; TASK_COMPLETE when done.",
        )
    clip_text(status_bundle())
    if not agent_running():
        start_agent()
    else:
        toast("Agent already running; status copied to clipboard")
    return 0

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("action", nargs="?", default="autopilot",
                    choices=["autopilot", "start", "stop", "restart", "status", "clip",
                             "set-next-task", "ensure-task"])
    ap.add_argument("arg", nargs="?", default="")
    args = ap.parse_args()

    if args.action == "start":
        start_agent()
    elif args.action == "stop":
        stop_agent()
        toast("Agent stopped")
    elif args.action == "restart":
        start_agent()
    elif args.action == "status":
        print(status_bundle())
    elif args.action == "clip":
        clip_text(status_bundle())
        toast("Status → clipboard")
    elif args.action == "set-next-task":
        set_next_task(args.arg or sys.stdin.read())
    elif args.action == "ensure-task":
        if not (META / "current_task.json").exists():
            cmd_autopilot()
        else:
            toast("Current task OK")
    else:
        return cmd_autopilot()

if __name__ == "__main__":
    sys.exit(main() or 0)
