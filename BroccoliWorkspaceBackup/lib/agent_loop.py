#!/usr/bin/env python3
"""
Continuous agent loop:
  - Run iter rounds until UI-based task_complete says done (no max iterations).
  - Toast + wait for user_next_task.txt (remind every 60s).
  - Repeat forever.
"""
import json, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "broccoli"
LIB, META, UI, REP = ROOT / "lib", ROOT / "meta", ROOT / "ui", ROOT / "reports"
sys.path.insert(0, str(LIB))

LOG = REP / "agent_loop.jsonl"

def log(row):
    REP.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("AGENT", row, flush=True)

def toast(msg):
    subprocess.run(["termux-toast", "-g", "bottom", msg[:100]], timeout=6, capture_output=True)

def cfg():
    return json.loads((META / "iter_loop.json").read_text()) if (META / "iter_loop.json").exists() else {}

def run_iter_once():
    r = subprocess.run([sys.executable, str(LIB / "iter_loop.py"), "--once"], timeout=600)
    return r.returncode

def capture():
    subprocess.run([sys.executable, str(LIB / "capture_chat_output.py")], timeout=180)

def apply_quarry():
    subprocess.run([sys.executable, str(LIB / "recursive_impl.py"), "--once"], timeout=600, capture_output=True)

def work_until_complete():
    from task_complete import decide_complete
    rules = json.loads((META / "task_completion_rules.json").read_text()) if (META / "task_completion_rules.json").exists() else {}
    need_streak = int(rules.get("min_consecutive_complete_dumps", 2))
    streak = 0
    loop_n = 0

    while True:
        loop_n += 1
        toast(f"Agent iter {loop_n}")
        log({"phase": "iter", "n": loop_n})

        # Ensure prompt exists
        if not (UI / "iter_prompt.txt").exists():
            c = cfg()
            (UI / "iter_prompt.txt").write_text(c.get("default_smoke_prompt", "Reply ITER_OK when step done."))

        run_iter_once()
        capture()

        # Optional: code apply + quarry inside iter_loop; extra quarry for completion signal
        subprocess.run([sys.executable, str(ROOT / "quarry_iter.py")], timeout=600, capture_output=True)

        verdict = decide_complete()
        log({"phase": "verdict", "n": loop_n, **verdict})

        if verdict.get("complete"):
            streak += 1
            if streak >= need_streak:
                log({"phase": "task_complete", "n": loop_n, "streak": streak})
                toast("Task complete (UI)", long=True)
                try:
                    from task_current import complete_task, load_current
                    cur = load_current()
                    complete_task(cur.get("task") or "agent_task", ok=True, detail=json.dumps(verdict.get("reasons", [])))
                except Exception:
                    pass
                return True
        else:
            streak = 0
            if verdict.get("should_continue"):
                # Build next prompt from output + dumps
                out = (UI / "iter_last_output.txt").read_text(errors="replace") if (UI / "iter_last_output.txt").exists() else ""
                test = (REP / "iter_test_tail.txt").read_text(errors="replace") if (REP / "iter_test_tail.txt").exists() else ""
                (UI / "iter_prompt.txt").write_text("\n".join([
                    "Continue until TASK_COMPLETE. UI verdict: not done yet.",
                    "Reasons: " + ", ".join(verdict.get("reasons", [])),
                    "Previous output:", out[-4000:],
                    "Test:", test[-1500:],
                    "Reply with fix as one code block, or ITER_OK / TASK_COMPLETE when done.",
                ]))
                (UI / "loop_inbox.txt").write_text((UI / "iter_prompt.txt").read_text())

        time.sleep(2)

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-wait", action="store_true", help="exit after one task complete")
    args = ap.parse_args()

    log({"phase": "agent_start"})
    toast("Agent loop running")

    while True:
        # Load user task if already in file before starting work
        ut = UI / "user_next_task.txt"
        if ut.exists() and ut.read_text().strip() and not ut.read_text().strip().startswith("#"):
            task = ut.read_text().strip()
            (UI / "iter_prompt.txt").write_text(task)
            (UI / "loop_inbox.txt").write_text(task)
            try:
                from task_current import start_task
                start_task(task[:80], detail="user_next_task")
            except Exception:
                pass
            ut.write_text("")

        work_until_complete()

        if args.no_wait:
            break

        from user_task_wait import wait_for_user_task
        wait_for_user_task()
        log({"phase": "new_task_loaded"})

if __name__ == "__main__":
    try:
        sys.exit(main() or 0)
    except KeyboardInterrupt:
        toast("Agent stopped")
        sys.exit(0)
