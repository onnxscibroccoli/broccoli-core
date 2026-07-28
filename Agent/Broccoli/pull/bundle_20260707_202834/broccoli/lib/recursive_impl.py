#!/usr/bin/env python3
"""
Recursive: UI dumps → chat reply → extract code blocks → apply → test → update task → next prompt.
"""
import json, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "broccoli"
LIB, META, UI, REP = ROOT / "lib", ROOT / "meta", ROOT / "ui", ROOT / "reports"
sys.path.insert(0, str(LIB))

INBOX = UI / "loop_inbox.txt"
OUTBOX = UI / "loop_outbox.txt"
RAW_REPLY = UI / "last_assistant_reply.txt"
CODE_MANIFEST = REP / "last_code_manifest.json"
LOG = REP / "recursive_impl.jsonl"

def policy():
    p = META / "recursive_policy.json"
    return json.loads(p.read_text()) if p.exists() else {}

def log(row):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("RECURSE", row, flush=True)

def toast(msg):
    subprocess.run(["termux-toast", "-g", "bottom", msg[:100]], timeout=6, capture_output=True)

def run_shell(cmd, t=300):
    log({"step": "run", "cmd": cmd[:200]})
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return -1, str(e)

def capture_reply_from_ui():
    from ui_dump_loop import dump_once, ensure_chat_ui
    from ui_state import classify

    pol = policy()
    ensure_chat_ui(max_rounds=3)
    for _ in range(int(pol.get("poll_reply_max", 12))):
        dump_once()
        state, meta = classify()
        if state == "CHAT_WITH_REPLY" and meta.get("last_reply"):
            text = meta["last_reply"]
            RAW_REPLY.write_text(text, encoding="utf-8")
            OUTBOX.write_text(text, encoding="utf-8")
            return text, meta
        time.sleep(float(pol.get("poll_reply_sec", 2)))
    if RAW_REPLY.exists():
        return RAW_REPLY.read_text(errors="replace"), {}
    return "", {}

def build_next_inbox(reply, test_out, manifest, task_name):
    blocks = manifest or []
    paths = [b["path"] for b in blocks]
    return "\n".join([
        "=== RECURSIVE ROUND (auto) ===",
        f"Task: {task_name}",
        f"Applied: {paths}",
        f"Test tail:\n{(test_out or '')[-1500:]}",
        "",
        "If tests failed, reply with ONE fixed code block only.",
        "If tests passed, reply with next feature as ONE code block + task name.",
    ])

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    pol = policy()
    from task_current import sync_from_queue, start_task, complete_task, update_from_chat_reply, load_current

    sync_from_queue()
    cur = load_current()
    task_name = cur.get("task") or "recursive_feature"
    start_task(task_name, detail="recursive_impl cycle")

    max_r = args.rounds or int(pol.get("max_rounds_per_run", 8))
    round_n = 0

    while round_n < max_r:
        round_n += 1
        log({"round": round_n, "phase": "ui_aware_send"})

        # 1) UI-aware send (uses loop_inbox)
        r = subprocess.run([sys.executable, str(LIB / "ui_aware_loop.py")], timeout=420)
        log({"round": round_n, "ui_aware_rc": r.returncode})

        # 2) Capture full assistant reply (extra dumps)
        reply, meta = capture_reply_from_ui()
        if not reply and OUTBOX.exists():
            reply = OUTBOX.read_text(errors="replace")
        log({"round": round_n, "reply_len": len(reply), "meta": meta})
        update_from_chat_reply(reply)

        if not reply:
            toast("No reply from UI")
            complete_task(task_name, ok=False, detail="no reply captured")
            return 2

        # 3) Extract code blocks → return as manifest (auto "return code block")
        from code_from_chat import extract_blocks, write_applied
        blocks = extract_blocks(reply)
        manifest = []
        if blocks and pol.get("auto_apply_code", True):
            apply_dir = pol.get("apply_dir", str(ROOT / "sandbox" / "applied"))
            manifest = write_applied(blocks, apply_dir)
            CODE_MANIFEST.write_text(json.dumps({"blocks": blocks, "manifest": manifest}, indent=2))
            log({"round": round_n, "code_blocks": len(blocks), "manifest": manifest})
            toast(f"Applied {len(blocks)} block(s)")

        # 4) Run applied scripts in order
        test_out = ""
        if manifest:
            for item in manifest:
                rc, out = run_shell(f'{item["runner"]} "{item["path"]}"', t=240)
                test_out += f"\n--- {item['path']} rc={rc} ---\n{out[-2000:]}"
                if rc != 0:
                    log({"round": round_n, "apply_fail": item["path"]})
                    break

        # 5) Auto test (quarry)
        if pol.get("auto_test_after_apply", True):
            rc, qout = run_shell(pol.get("test_command", f'python3 "{ROOT}/quarry_iter.py"'), t=600)
            test_out += f"\n--- quarry rc={rc} ---\n{qout[-3000:]}"
            (REP / "quarry_after_apply.txt").write_text(test_out[-8000:])
            ok = rc == 0 or "11 / 11" in qout or "10 / 11" in qout and "FAIL dump_ui" in qout
        else:
            ok = not manifest or "rc=0" in test_out

        # 6) Update task + queue
        complete_task(task_name, ok=ok, detail=test_out[-200:])
        sync_from_queue()
        cur = load_current()
        task_name = cur.get("task") or task_name

        # 7) Seed next inbox for recursive Grok round
        next_msg = build_next_inbox(reply, test_out, manifest, task_name)
        INBOX.write_text(next_msg)
        (UI / "last_code_blocks.txt").write_text("\n\n---\n\n".join(blocks) if blocks else "")
        log({"round": round_n, "ok": ok, "next_inbox_len": len(next_msg)})

        if args.once:
            break
        if ok and not blocks:
            break
        if round_n >= max_r:
            break

    toast("Recursive done")
    return 0

if __name__ == "__main__":
    sys.exit(main())
