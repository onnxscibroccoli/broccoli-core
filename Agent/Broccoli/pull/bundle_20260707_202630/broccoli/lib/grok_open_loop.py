#!/usr/bin/env python3
"""
Loop: read response queue → rish adb open Grok activity → chat FG → wait for user/Grok → log → next.
Driven by ~/broccoli/ui/loop_inbox.txt and loop_outbox.txt
"""
import json, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "broccoli"
LIB, UI, REP, META = ROOT / "lib", ROOT / "ui", ROOT / "reports", ROOT / "meta"
sys.path.insert(0, str(LIB))

INBOX = UI / "loop_inbox.txt"      # paste next instruction / my reply tail here
OUTBOX = UI / "loop_outbox.txt"      # what to send to Grok composer
LOG = REP / "grok_open_loop.jsonl"
STATE = META / "loop_state.json"

def toast(msg):
    subprocess.run(["termux-toast", "-g", "bottom", msg[:100]], timeout=6, capture_output=True)

def append_log(row):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")

def read_inbox():
    if not INBOX.exists():
        return ""
    return INBOX.read_text(errors="replace").strip()

def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {"round": 0, "last_activity_cmd": ""}

def save_state(s):
    STATE.write_text(json.dumps(s, indent=2))

def one_round(round_n, instruction):
    from rish_adb import open_grok_activity, grok_focused

    toast(f"Loop r{round_n}: open Grok")
    ok, cmd, detail = open_grok_activity()
    append_log({"round": round_n, "step": "rish_open", "ok": ok, "cmd": cmd, "detail": detail[:300]})

    if not ok:
        toast("rish open weak — chat_fg fallback")
        subprocess.run([sys.executable, str(LIB / "grok_chat_foreground.py")], timeout=320)
    else:
        # Still run Ask + composer taps (paramount)
        subprocess.run([sys.executable, str(LIB / "grok_chat_foreground.py")], timeout=320)

    append_log({"round": round_n, "step": "chat_foreground", "grok_focus": grok_focused()})

    if instruction:
        OUTBOX.write_text(instruction)
        boot = HOME / "broccoli_bootstrap.py"
        if boot.exists():
            # If you have inject_text / send — try; else user pastes OUTBOX manually
            for sub in (
                f'python3 "{boot}" focus_composer 2>/dev/null',
                f'python3 "{boot}" inject_text "$(cat {OUTBOX})" 2>/dev/null',
                f'python3 "{boot}" send_prompt "$(cat {OUTBOX})" 2>/dev/null',
            ):
                subprocess.run(sub, shell=True, timeout=45, capture_output=True)

    toast(f"Round {round_n}: collaborate in Grok")
    print(f"ROUND {round_n}: Grok open. INBOX={INBOX} OUTBOX={OUTBOX}", flush=True)
    print("Paste Grok reply to loop_inbox.txt for next round, or empty inbox to idle-skip.", flush=True)
    return ok

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=0, help="0 = infinite until Ctrl+C")
    ap.add_argument("--interval", type=int, default=30, help="sec between rounds if inbox empty")
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    st = load_state()
    n = st.get("round", 0)

    while True:
        n += 1
        st["round"] = n
        instr = read_inbox()
        if not instr and not args.once:
            print("inbox empty — sleep", args.interval, flush=True)
            time.sleep(args.interval)
            if args.rounds and n - st.get("round_start", n) >= args.rounds:
                break
            continue

        one_round(n, instr)
        if instr:
            # clear consumed instruction (keep file for audit in .bak)
            (UI / "loop_inbox.consumed").write_text(instr)
            INBOX.write_text("")

        save_state(st)
        if args.once:
            break
        if args.rounds and n >= args.rounds:
            break
        time.sleep(2)

if __name__ == "__main__":
    main()
