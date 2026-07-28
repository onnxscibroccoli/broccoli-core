
#!/usr/bin/env python3
"""Pause automation and ask the human to complete a step (login, OAuth, etc.)."""
import json, subprocess, sys, time
from pathlib import Path

R = Path.home() / "broccoli"
STATE = R / "tasks" / "state.json"
WAIT_REP = R / "reports" / "WAITING_USER.txt"
PENDING = R / "user" / "PENDING.md"

def load_state():
    if STATE.is_file():
        try:
            return json.loads(STATE.read_text())
        except Exception:
            pass
    return {}

def save_state(d):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, indent=2) + "\n")

def toast(msg):
    short = (msg or "complete the step on screen")[:120]
    subprocess.run(
        ["termux-toast", "-s", "Broccoli: Waiting for you — " + short],
        timeout=8, check=False,
    )
    subprocess.run(["termux-vibrate", "-d", "300"], timeout=5, check=False)

def parse_wait(text):
    m = re.search(r"(?m)^WAIT_FOR_USER:\s*(.+)$", text or "")
    if m:
        return m.group(1).strip()[:500]
    m = re.search(r"(?m)^##\s*User must\s*\n(.+)", text or "", re.I)
    if m:
        return m.group(1).strip()[:500]
    return None

def wait_for(label, detail=""):
    label = (label or "complete the required step").strip()
    d = load_state()
    d["status"] = "WAITING_USER"
    d["wait_label"] = label
    d["wait_since"] = time.strftime("%Y-%m-%d %H:%M:%S")
    d["reason"] = "user_interaction_required"
    save_state(d)
    body = (
        "WAITING_FOR_USER\n"
        "label: %s\n"
        "detail: %s\n"
        "When done on the phone: brocc user-done\n"
        "Or: brocc inject 'USER_ACK: <what you did>'\n"
    ) % (label, (detail or label)[:2000])
    WAIT_REP.parent.mkdir(parents=True, exist_ok=True)
    WAIT_REP.write_text(body)
    PENDING.parent.mkdir(parents=True, exist_ok=True)
    PENDING.write_text("WAIT_FOR_USER: %s\n(daemon paused until user-done)\n" % label)
    toast(label)
    try:
        subprocess.run(["termux-clipboard-set"], input=body.encode(), timeout=8, check=False)
    except Exception:
        pass
    print("WAITING_USER", label)
    return 0

def user_done(note=""):
    d = load_state()
    d["status"] = "RUNNING"
    d.pop("wait_label", None)
    d.pop("wait_since", None)
    d["reason"] = ""
    if note:
        d["user_done_note"] = note[:500]
    save_state(d)
    if WAIT_REP.is_file():
        WAIT_REP.unlink(missing_ok=True)
    if note:
        with open(PENDING, "a", encoding="utf-8") as f:
            f.write("\nUSER_DONE: %s\n" % note[:800])
    subprocess.run(["termux-toast", "-s", "Broccoli: resumed"], timeout=5, check=False)
    print("RUNNING")
    return 0

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "wait":
        label = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "complete the step on screen"
        sys.exit(wait_for(label))
    if cmd == "done":
        note = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        sys.exit(user_done(note))
    if cmd == "check-job":
        path = sys.argv[2] if len(sys.argv) > 2 else ""
        text = Path(path).read_text(errors="replace") if path and Path(path).is_file() else sys.stdin.read()
        w = parse_wait(text)
        if w:
            sys.exit(wait_for(w))
        sys.exit(1)
    if cmd == "status":
        print(json.dumps(load_state(), indent=2))
        return
    print("usage: wait <label>|done [note]|check-job <file>|status")

if __name__ == "__main__":
    main()
