import json, os, subprocess, time
from pathlib import Path
BRO = Path.home() / "broccoli"
GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
PREFIX = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")

def _sh(cmd, t=12):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 1, str(e)

def notify(title, content, ongoing=True):
    if not (Path(PREFIX)/"bin/termux-notification").is_file():
        return False
    bro = str(BRO)
    esc = lambda s: s.replace('"', '\\"')[:120]
    cmd = (
        f'termux-notification --id broccoli-ctl --priority high '
        f'{"--ongoing " if ongoing else ""}'
        f'-t "{esc(title)}" -c "{esc(content)}" '
        f'--button1 "Send" --button1-action "touch {bro}/inbox/trigger; termux-toast queued" '
        f'--button2 "Pause" --button2-action "touch {bro}/state/PAUSE; termux-toast paused" '
        f'--button3 "Resume" --button3-action "rm -f {bro}/state/PAUSE; touch {bro}/inbox/trigger; termux-toast resume"'
    )
    return _sh(cmd)[0] == 0

def list_notifs():
    if not (Path(PREFIX)/"bin/termux-notification-list").is_file():
        return []
    rc, out = _sh("termux-notification-list", 15)
    if rc != 0:
        return []
    try:
        return json.loads(out) if out.strip() else []
    except json.JSONDecodeError:
        return []

def recv_from_grok_notif(before="", max_wait=18.0):
    t0 = time.time()
    seen = {before} if before else set()
    while time.time() - t0 < max_wait:
        for n in list_notifs():
            pkg = (n.get("package") or n.get("packageName") or "")
            if GROK not in pkg:
                continue
            blob = " ".join(filter(None, [
                (n.get("title") or "").strip(),
                (n.get("content") or n.get("text") or "").strip(),
            ]))
            if len(blob) < 4 or blob in seen:
                continue
            seen.add(blob)
            (BRO/"inbox/grok_reply_notif.txt").write_text(blob, encoding="utf-8")
            return blob, {"source": "notification-list"}
        time.sleep(0.8)
    return "", {"source": "notification-list", "timeout": True}
