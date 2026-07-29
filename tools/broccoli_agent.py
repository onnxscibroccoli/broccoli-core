
#!/usr/bin/env python3
"""Foreground Grok → brocc send (no clipboard). Clipboard helper for tests/fallback only."""
import json, re, subprocess, sys, time, shutil, tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

B = Path.home() / "broccoli"
ENV = B / "meta" / "wire_coords.env"
XML = B / "reports" / "ui_dump.xml"
LOG = B / "reports" / "agent_loop.log"
CLIP_TEST = B / "reports/last_clipboard.txt"

def log(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}\n")

def load_env() -> dict:
    o = {"GROK_PKG": "com.ai.x.grok", "COLLAB_POLL_SEC": "0"}
    if ENV.is_file():
        for line in ENV.read_text(errors="replace").splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                o[k.strip()] = v.strip()
    return o

def rish(cmd: str, timeout: int = 60):
    return subprocess.run(["rish", "-c", cmd], capture_output=True, text=True, timeout=timeout)

def has_brocc() -> bool:
    return shutil.which("brocc") is not None

def clipboard_set_verify(msg: str) -> bool:
    """Termux-only. Never call clipboard via rish."""
    msg = msg if isinstance(msg, str) else str(msg)
    CLIP_TEST.write_text(msg, encoding="utf-8")
    # Method A: stdin from file (most reliable for multiline)
    r = subprocess.run(
        ["sh", "-c", "termux-clipboard-set < \"$1\"", "_", str(CLIP_TEST)],
        capture_output=True, text=True, timeout=15,
    )
    time.sleep(0.35)
    got = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, timeout=15)
    g = got.stdout or ""
    # Compare prefix + length (Android sometimes trims trailing newline)
    want_head = msg[:48]
    got_head = g[:48]
    ok = len(msg) > 0 and want_head == got_head and abs(len(g) - len(msg)) <= 2
    log(f"{'OK' if ok else 'FAIL'} clipboard_set want_len={len(msg)} got_len={len(g)} head_want={want_head!r} head_got={got_head!r} rc_set={r.returncode}")
    if not ok and len(msg) < 500:
        # Method B: single argument
        subprocess.run(["termux-clipboard-set", msg], capture_output=True, text=True, timeout=15)
        time.sleep(0.35)
        got2 = subprocess.run(["termux-clipboard-get"], capture_output=True, text=True, timeout=15)
        g2 = got2.stdout or ""
        ok = msg[:48] == g2[:48] and abs(len(g2) - len(msg)) <= 2
        log(f"{'OK' if ok else 'FAIL'} clipboard_set_retry_b head_got={g2[:48]!r}")
    return ok

def sync_dump() -> bool:
    if has_brocc():
        subprocess.run(["brocc", "dump"], capture_output=True, text=True, timeout=90)
    if XML.is_file() and XML.stat().st_size > 800:
        return True
    rish("uiautomator dump /data/local/tmp/broccoli_ui.xml")
    r = rish("cat /data/local/tmp/broccoli_ui.xml")
    if r.stdout and len(r.stdout) > 800:
        XML.write_text(r.stdout, encoding="utf-8", errors="replace")
        return True
    return False

def foreground_grok(cfg: dict) -> None:
    pkg = cfg.get("GROK_PKG", "com.ai.x.grok")
    log(f"STEP foreground_grok pkg={pkg}")
    if has_brocc():
        subprocess.run(["brocc", "launch-grok"], capture_output=True, text=True, timeout=90)
        time.sleep(1.2)
    rish(f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {pkg}")
    time.sleep(0.8)
    for _ in range(6):
        if sync_dump():
            raw = XML.read_text(errors="replace")
            if pkg in raw or "grok" in raw.lower():
                log("OK grok_foreground")
                return
        time.sleep(0.4)
    log("WARN grok_foreground_unconfirmed")

def wire_brocc_only(msg: str) -> int:
    cfg = load_env()
    foreground_grok(cfg)
    if not has_brocc():
        log("FAIL no_brocc")
        return 1
    log(f"TRY brocc_send len={len(msg)}")
    r = subprocess.run(["brocc", "send", msg], capture_output=True, text=True, timeout=180)
    out = (r.stdout or "") + (r.stderr or "")
    log(f"brocc_send rc={r.returncode} tail={out[-150:].replace(chr(10), ' ')}")
    if "OK sent" in out or (r.returncode == 0 and "FAIL" not in out):
        log("OK wire_brocc_no_clipboard")
        return 0
    log("FAIL wire_brocc")
    return 1

def drain_queue() -> None:
    q = B / "queue" / "agent_task.txt"
    if not q.is_file() or q.stat().st_size == 0:
        return
    msg = q.read_text(encoding="utf-8", errors="replace")[:3800]
    log(f"TRY queue_bytes={len(msg)}")
    if wire_brocc_only(msg) == 0:
        q.write_text("")
        log("OK queue_cleared")
    else:
        log("RETRY keep_queue")

def loop_forever() -> None:
    log("OK agent v4 foreground_brocc_send NO_CLIPBOARD_ON_WIRE")
    while True:
        drain_queue()
        time.sleep(float(load_env().get("COLLAB_POLL_SEC", "0") or 0))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clip-test":
        m = sys.argv[2] if len(sys.argv) > 2 else f"CLIP_TEST_{int(time.time())}"
        sys.exit(0 if clipboard_set_verify(m) else 1)
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        drain_queue()
        sys.exit(0)
    if len(sys.argv) > 2 and sys.argv[1] == "send":
        sys.exit(wire_brocc_only(" ".join(sys.argv[2:])))
    loop_forever()
