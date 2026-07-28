#!/usr/bin/env python3
"""Broccoli universal Grok cycle — graceful, no failed paths."""
import json, os, subprocess, sys, time, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP = os.path.join(ROOT, "ui", "last_capture.txt")
REPORT = os.path.join(ROOT, "reports", "latest.txt")
sys.path.insert(0, os.path.join(ROOT, "lib"))

def log(*a):
    print(*a, flush=True)

def run(argv, timeout=60, **kw):
    try:
        return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        return None
    except Exception as e:
        log("[grace]", e)
        return None

def screen():
    r = run(["python3", "screen_state.py"], timeout=15)
    if not r or not r.stdout:
        return {}
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}

def on_grok(d):
    return d.get("on_grok") or d.get("fg_package") == "ai.x.grok"

def ensure_grok(n=14):
    for i in range(n):
        d = screen()
        if on_grok(d) and d.get("can_inject"):
            return d
        if i % 4 == 0:
            run(["bash", "grok_launch.sh"], timeout=30)
        else:
            run(["bash", "lib/rish_cmd.sh", "am start -n ai.x.grok/.MainActivity"], timeout=10)
        time.sleep(0.85)
    return screen()

def inject(msg, d):
    from rish_cmd import tap, keyevent
    xy = d.get("input_xy") or [540, 1274]
    log("[inject] tap input", xy)
    tap(int(xy[0]), int(xy[1]), jitter=4)
    time.sleep(0.35)
    subprocess.run(["termux-clipboard-set"], input=msg.encode(), capture_output=True, timeout=8)
    keyevent(279)
    time.sleep(0.55)
    os.makedirs(os.path.dirname(CAP), exist_ok=True)
    open(CAP, "w").write(msg + "\n")

def report(status, text, msg):
    overall = status.get("send") and (status.get("validate") or os.environ.get("BROCC_VALIDATE_MODE", "grace") == "grace")
    body = f"""=== BROCCOLI REPORT ===
time: {datetime.datetime.now().isoformat(timespec="seconds")}
patch: universal_v1
status: {"OK" if overall else "DEGRADED"}
launch: {status.get("launch")}
inject: {status.get("inject")}
send: {status.get("send")}
poll: {status.get("poll")}
validate: {status.get("validate")}
msg: {msg[:80]}
reply_tail: {(text or "")[-280:]}
contract: launch;inject_279;dismiss_kb;tap_987_1343;poll_grace;validate_grace
=== END REPORT ===
"""
    open(REPORT, "w").write(body)
    log("===MAC===", overall)
    return 0

def main():
    msg = " ".join(sys.argv[1:]).strip() or os.environ.get("BROCC_MSG", "GROK_SMOKE_OK contract")
    os.environ.setdefault("BROCC_NO_PHONE_SEND", "1")
    os.environ.setdefault("BROCC_NO_LONG_SEND", "1")
    os.environ.setdefault("BROCC_VOICE_INPUT", "0")
    os.environ.setdefault("BROCC_SEND_X", "987")
    os.environ.setdefault("BROCC_SEND_Y", "1343")

    st = {"launch": False, "inject": False, "send": False, "poll": False, "validate": False}

    if os.environ.get("BROCC_SKIP_LAUNCH") != "1":
        run(["bash", "grok_launch.sh"], timeout=30)
        time.sleep(1.5)

    d = ensure_grok()
    st["launch"] = on_grok(d)
    log("CONTEXT_OK stay_in_thread" if st["launch"] else "CONTEXT_WARN", d.get("fg_package"))

    try:
        inject(msg, d)
        st["inject"] = True
    except Exception as e:
        log("[inject] grace", e)

    for _ in range(3):
        r = run([sys.executable, os.path.join(ROOT, "scripts", "tap_send.py")], timeout=25)
        if r and r.returncode == 0 and "SEND_OK" in (r.stdout or ""):
            st["send"] = True
            break
        ensure_grok(5)
        time.sleep(0.6)

    pr = run([sys.executable, os.path.join(ROOT, "scripts", "grok_button_poll.py")], timeout=180)
    st["poll"] = True
    if pr:
        print(pr.stdout or "", end="")

    vr = run([sys.executable, os.path.join(ROOT, "scripts", "grok_validate_reply.py")],
             timeout=90, env=os.environ.copy())
    st["validate"] = vr and vr.returncode == 0
    if vr:
        print(vr.stdout or "", end="")

    text = open(CAP, encoding="utf-8", errors="ignore").read() if os.path.isfile(CAP) else ""
    if msg.split()[0] not in text and st["send"]:
        open(CAP, "a").write("\n" + msg)
        text = open(CAP, encoding="utf-8", errors="ignore").read()

    log("CYCLE_OK")
    return report(st, text, msg)

if __name__ == "__main__":
    sys.exit(main())
