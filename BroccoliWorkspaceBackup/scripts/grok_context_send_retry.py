#!/usr/bin/env python3
"""Clipboard → launch → context → scroll → paste → send. 4x1s per step."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
from broccoli_retry import (
    DELAY_SEC,
    RETRIES,
    StepFail,
    dump_text,
    grok_foreground,
    has_input,
    has_send,
    launch_grok,
    run_step,
    set_clipboard,
    snap,
    tap_profile,
    tap_send_from_dump,
)

os.environ.setdefault("BROCC_NO_SELF_MUTATE", "1")


def inject(msg: str) -> bool:
    inj = ROOT / "chat_inject.sh"
    if inj.is_file():
        set_clipboard(msg)
        r = subprocess.run(["bash", str(inj), msg], cwd=ROOT, capture_output=True, timeout=20)
        return r.returncode == 0
    set_clipboard(msg)
    if tap_profile("input") or tap_profile("compose"):
        time.sleep(0.3)
        subprocess.run(["input", "keyevent", "279"], capture_output=True)  # paste
        return True
    return False


def is_blank(xml: str) -> bool:
    if has_input(xml) and grok_foreground(xml):
        # has input but maybe new chat — weak signal
        if "new chat" in xml.lower() or "start" in xml.lower():
            return True
    if not grok_foreground(xml):
        return True
    return "recyclerview" not in xml.lower() and "message" not in xml.lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("message", nargs="?", default="")
    ap.add_argument("--conv-index", type=int, default=int(os.environ.get("CONV_INDEX", "0")))
    ap.add_argument("--wait-user-sec", type=int, default=int(os.environ.get("WAIT_USER_SEC", "0")))
    args = ap.parse_args()

    msg = args.message.strip() or subprocess.run(
        ["termux-clipboard-get"], capture_output=True, text=True, timeout=5
    ).stdout.strip()
    if not msg:
        print("CTX_FAIL_EMPTY_CLIPBOARD")
        sys.exit(1)

    print(f"[ctx] retries={RETRIES} delay={DELAY_SEC}s")

    # 0 clipboard first
    run_step("clipboard", lambda: (set_clipboard(msg), True)[1], "termux-api clipboard")

    # 1 launch (brocc launch-grok — required for smoke pass)
    if os.environ.get("BROCC_SKIP_LAUNCH") != "1":
        run_step("launch_grok", lambda: (
            subprocess.run(["bash", str(ROOT / "bin" / "brocc"), "launch-grok"],
                           cwd=ROOT, timeout=25).returncode == 0
        ), "Run: cd ~/broccoli && brocc launch-grok")
        os.environ["BROCC_LAUNCHED"] = "1"

    def step_launch():
        launch_grok()
        time.sleep(0.8)
        xml = dump_text()
        return grok_foreground(xml)

    run_step("launch", step_launch, "Open Grok manually; check a11y dump")

    # 2 optional user window (you help)
    if args.wait_user_sec > 0:
        print(f"[ctx] waiting for you {args.wait_user_sec}s — open your thread")
        time.sleep(args.wait_user_sec)

    # 3 context (menu + pick conv if blank)
    def step_context():
        xml = dump_text()
        if not is_blank(xml) and has_input(xml):
            return True
        if tap_profile("menu") or tap_profile("drawer"):
            time.sleep(0.6)
        else:
            subprocess.run(["input", "tap", "90", "180"], capture_output=True)
        time.sleep(0.5)
        xml = dump_text()
        prof = ROOT / "chat_profile.json"
        if prof.is_file():
            j = json.loads(prof.read_text(encoding="utf-8"))
            items = j.get("conversation_items") or []
            if args.conv_index < len(items):
                it = items[args.conv_index]
                subprocess.run(
                    ["input", "tap", str(it["x"]), str(it["y"])],
                    capture_output=True,
                )
                time.sleep(0.8)
        xml = dump_text()
        return grok_foreground(xml) and has_input(xml) and not is_blank(xml)

    run_step(
        "context",
        step_context,
        f"Tap menu → conversation[{args.conv_index}] OR set WAIT_USER_SEC=15",
    )

    # 4 scroll bottom
    def step_scroll():
        if tap_profile("scroll_down") or tap_profile("jump_bottom"):
            time.sleep(0.4)
            return True
        subprocess.run(["input", "swipe", "540", "1800", "540", "900", "250"], capture_output=True)
        return True

    run_step("scroll", step_scroll, "Tap scroll-down chevron once")

    # 5 paste
    run_step("paste", lambda: inject(msg), "Focus input; check chat_inject.sh")

    # 6 send (critical)
    def step_send():
        xml = dump_text()
        if not has_send(xml) and not (ROOT / "chat_profile.json").is_file():
            raise StepFail("SEND_NOT_IN_DUMP", "Learn send button coords", fatal=False)
        return tap_send_from_dump(xml) or (
            (ROOT / "chat_copy_tap.py").is_file()
            and subprocess.run(
                ["python3", str(ROOT / "chat_copy_tap.py"), "send"],
                cwd=ROOT,
                capture_output=True,
            ).returncode
            == 0
        )

    run_step("send", step_send, "Tap Send once; update chat_profile.json send")

    print("CTX_OK")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except StepFail as e:
        print(f"CTX_FAIL_{e.code}")
        if e.hint:
            print(f"HINT: {e.hint}")
        try:
            xml = (ROOT / "window_dump.xml").read_text(encoding="utf-8", errors="ignore")[:2000]
            for kw in ("Send", "EditText", "navigation", "menu", "Grok"):
                if kw.lower() in xml.lower():
                    print(f"DUMP_HAS: {kw}")
        except Exception:
            pass
        sys.exit(1)
