#!/usr/bin/env python3
"""
Broccoli / Grok Android automation (Termux + Shizuku rish).
Complete paths: launch, compose, send, deliver reply, smoke, queue.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
import sys as _sys
_sys.path.insert(0, str(Path.home() / "broccoli" / "lib"))
try:
    import dump_ui_fallback as _duf
except Exception:
    _duf = None
from typing import List, Optional, Tuple

HOME = Path.home()
REPORTS = HOME / "broccoli" / "reports"
QUEUE = HOME / "broccoli" / "queue" / "pending.txt"
META = HOME / "broccoli" / "meta"
DUMP_SD = "/data/local/tmp/broccoli_ui.xml"
DUMP_LOCAL = REPORTS / "last_ui_dump.xml"
REPLY_LOCAL = REPORTS / "last_grok_reply.txt"
PKG = "ai.x.grok"
POLL_INTERVAL = 3
DEFAULT_ASK_TIMEOUT = 120

CHIP_RE = re.compile(
    r"Grok System Architecture|xAI Competitor|Explore Grok|Competitor Analysis|Imagine",
    re.I,
)
SMOKE_TOKEN = "GROK_SMOKE_OK"


def log(*a):
    print(*a, flush=True)


def rish_cmd(cmd: str, timeout: int = 60) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["rish", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError:
        return 127, "", "rish not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def rish_script(script: str, timeout: int = 90) -> Tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["rish"],
            input=script,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except FileNotFoundError:
        return 127, "", "rish not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def shell_clipboard_set(text: str) -> None:
    # Android 10+ shell clipboard (works under rish shell uid)
    esc = text.replace("\\", "\\\\").replace('"', '\\"')
    rish_cmd(f'cmd clipboard set "{esc}"', timeout=15)
    # Clipper broadcast fallback
    rish_cmd(
        f'am broadcast -a clipper.set -e text "{esc}" 2>/dev/null || true',
        timeout=10,
    )


def launch_grok(wait: float = 2.0) -> None:
    log("STEP launch_grok")
    import subprocess
    subprocess.run(["bash", str(Path.home() / "broccoli/lib/launch_grok_native.sh")], check=False, timeout=20)
    time.sleep(wait)

def dump_ui_raw() -> str:
    script = f"""set -e
rm -f {DUMP_SD} 2>/dev/null || true
uiautomator dump {DUMP_SD} 2>/dev/null || cmd uiautomator dump {DUMP_SD} 2>/dev/null
cat {DUMP_SD} 2>/dev/null
"""
    _, out, err = rish_script(script, timeout=90)
    raw = out if out.strip() else err
    if "<?xml" in raw:
        xml = raw[raw.find("<?xml") :]
    elif "<hierarchy" in raw:
        xml = raw[raw.find("<hierarchy") :]
    else:
        xml = raw.strip()
    if xml and "<hierarchy" in xml:
        REPORTS.mkdir(parents=True, exist_ok=True)
        DUMP_LOCAL.write_text(xml, encoding="utf-8", errors="replace")
    return xml if "<hierarchy" in (xml or "") else ""


def dump_ui() -> str:
    if _duf:
        _t, _n, _p = _duf.read_best_xml()
        if _n >= 8000 and '<hierarchy' in _t:
            log('STEP dump_ui fallback early', _n, _p)
            return _t
    log("STEP dump_ui")
    xml = dump_ui_raw()
    sz = len(xml)
    log("  file_bytes", sz)
    if sz < 1024:
        log("  FAIL: no hierarchy in file  # BROCC: retry full dump")
        time.sleep(1)
        xml = dump_ui_raw()
        log("  file_bytes", len(xml))
    return xml


@dataclass
class UINode:
    text: str
    resource_id: str
    content_desc: str
    bounds: str
    klass: str
    clickable: bool
    package: str


def parse_nodes(xml: str) -> List[UINode]:
    if not xml:
        return []
    nodes: List[UINode] = []
    for m in re.finditer(r"<node\s+([^>]+)/?>", xml):
        attrs = m.group(1)

        def attr(name: str) -> str:
            mm = re.search(rf'{name}="([^"]*)"', attrs)
            return mm.group(1) if mm else ""

        nodes.append(
            UINode(
                text=attr("text"),
                resource_id=attr("resource-id"),
                content_desc=attr("content-desc"),
                bounds=attr("bounds"),
                klass=attr("class"),
                clickable=attr("clickable") == "true",
                package=attr("package"),
            )
        )
    return nodes


def bounds_center(bounds: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
    if not m:
        return None
    x1, y1, x2, y2 = map(int, m.groups())
    return (x1 + x2) // 2, (y1 + y2) // 2


def tap(cx: int, cy: int) -> None:
    rish_cmd(f"input tap {cx} {cy}")
    time.sleep(0.35)


def keyevent(code: int) -> None:
    rish_cmd(f"input keyevent {code}")
    time.sleep(0.25)


def ensure_ask_tab(xml: str) -> str:
    """Imagine tab breaks text compose; select Ask."""
    for n in parse_nodes(xml):
        if n.package != PKG:
            continue
        if n.content_desc == "Ask" or (n.text == "Ask" and "TextView" in n.klass):
            c = bounds_center(n.bounds)
            if c:
                log("STEP ensure_ask_tab tap Ask")
                tap(*c)
                time.sleep(0.8)
                return dump_ui()
    return xml


def find_composer(nodes: List[UINode]) -> Optional[UINode]:
    for n in nodes:
        if n.package == PKG and n.resource_id == "chat_text_input":
            return n
    for n in nodes:
        if n.package == PKG and "EditText" in n.klass:
            return n
    return None


def find_send(nodes: List[UINode]) -> Optional[UINode]:
    for desc in ("Send message", "Send", "Submit"):
        for n in nodes:
            if n.package == PKG and n.content_desc == desc and n.clickable:
                return n
    # clickable ImageView near bottom-right when field has text
    for n in nodes:
        if n.package != PKG or not n.clickable:
            continue
        if "ImageView" not in n.klass:
            continue
        c = bounds_center(n.bounds)
        if c and c[0] > 900 and c[1] > 2000:
            if n.content_desc and "Voice" not in n.content_desc and "images" not in n.content_desc.lower():
                return n
    return None


def grok_fill_test() -> int:
    launch_grok()
    xml = ensure_ask_tab(dump_ui())
    nodes = parse_nodes(xml)
    comp = find_composer(nodes)
    if not comp:
        log("FAIL fill_test: no chat_text_input")
        return 1
    c = bounds_center(comp.bounds)
    if not c:
        log("FAIL fill_test: bad bounds")
        return 1
    log("STEP tap composer", comp.bounds)
    tap(*c)
    time.sleep(0.4)
    test = "BROCC_FILL_TEST"
    shell_clipboard_set(test)
    keyevent(279)  # PASTE
    time.sleep(0.6)
    xml2 = dump_ui()
    if test in xml2 or "BROCC_FILL" in xml2:
        log("OK fill_test pasted")
        return 0
    # fallback: type ASCII
    rish_cmd(f'input text BROCC_FILL_TEST')
    time.sleep(0.5)
    xml3 = dump_ui()
    if "BROCC_FILL" in xml3:
        log("OK fill_test typed")
        return 0
    log("FAIL fill_test: composer empty in dump")
    return 1


def grok_send_text(message: str, *, do_launch: bool = True) -> int:
    if do_launch:
        launch_grok()
    xml = ensure_ask_tab(dump_ui())
    nodes = parse_nodes(xml)
    comp = find_composer(nodes)
    if not comp:
        log("FAIL send: no composer")
        return 1
    c = bounds_center(comp.bounds)
    if not c:
        log("FAIL send: bounds")
        return 1
    log("STEP grok_send tap composer")
    tap(*c)
    time.sleep(0.5)
    # clear-ish: select all + del (best effort)
    keyevent(122)  # MOVE_HOME
    shell_clipboard_set(message)
    subprocess.run([sys.executable, str(Path.home() / "broccoli/lib/grok_send_tap.py"), message], check=False, timeout=120)
    keyevent(279)  # PASTE
    time.sleep(0.7)
    xml2 = dump_ui()
    nodes2 = parse_nodes(xml2)
    send = find_send(nodes2)
    if send:
        sc = bounds_center(send.bounds)
        if sc:
            log("STEP grok_send tap send", send.content_desc or send.klass)
            tap(*sc)
        else:
            keyevent(66)
    else:
        log("STEP grok_send keyevent ENTER")
        keyevent(66)
    time.sleep(1.0)
    log("OK sent")
    return 0


def _smoke_ok(xml: str) -> bool:
    if not xml:
        return False
    return bool(
        re.search(rf'text="{re.escape(SMOKE_TOKEN)}"', xml)
        or re.search(rf">{re.escape(SMOKE_TOKEN)}<", xml)
    )


def _extract_assistant_reply(xml: str, *, user_prompt: Optional[str] = None) -> str:
    if not xml:
        return ""
    candidates: List[Tuple[int, str]] = []
    for n in parse_nodes(xml):
        if n.package != PKG:
            continue
        if "TextView" not in n.klass:
            continue
        t = (n.text or "").strip()
        if not t:
            continue
        if CHIP_RE.search(t):
            continue
        if t in ("Ask", "Imagine", "Ask anything"):
            continue
        if user_prompt and t == user_prompt.strip():
            continue
        if t.startswith("Reply with only") and user_prompt and user_prompt.strip() in t:
            continue
        # user bubble often right-aligned large x1
        m = re.match(r"\[(\d+),", n.bounds or "")
        x1 = int(m.group(1)) if m else 0
        candidates.append((x1, t))
    if not candidates:
        return ""
    # prefer left-aligned assistant (small x1), else last non-chip
    candidates.sort(key=lambda x: x[0])
    left = [t for x, t in candidates if x < 400]
    if left:
        return left[-1]
    return candidates[-1][1]


def grok_poll_reply(
    timeout: int = DEFAULT_ASK_TIMEOUT,
    *,
    user_prompt: Optional[str] = None,
    want_token: Optional[str] = None,
) -> str:
    deadline = time.time() + timeout
    last = ""
    poll_n = 0
    while time.time() < deadline:
        poll_n += 1
        log("poll", poll_n, "elapsed", int(timeout - (deadline - time.time())), "s")
        xml = dump_ui()
        if want_token and _smoke_ok(xml):
            return SMOKE_TOKEN
        reply = _extract_assistant_reply(xml, user_prompt=user_prompt)
        if reply and reply != last:
            last = reply
            if want_token and want_token in reply:
                return reply
            if not want_token and len(reply) >= 1:
                # wait until stable-ish (2 identical reads)
                time.sleep(POLL_INTERVAL)
                xml2 = dump_ui()
                reply2 = _extract_assistant_reply(xml2, user_prompt=user_prompt)
                if reply2 == reply or (reply2 and len(reply2) >= len(reply)):
                    REPORTS.mkdir(parents=True, exist_ok=True)
                    REPLY_LOCAL.write_text(reply2 or reply, encoding="utf-8")
                    return reply2 or reply
        time.sleep(POLL_INTERVAL)
    return last


def grok_ask(message: str, timeout: int = DEFAULT_ASK_TIMEOUT) -> int:
    if grok_send_text(message) != 0:
        return 1
    log("STEP grok_ask poll")
    reply = grok_poll_reply(timeout, user_prompt=message)
    if not reply:
        log("=== BROCCOLI_DONE === grok FAIL: empty reply")
        return 1
    print(reply)
    log("=== BROCCOLI_DONE === grok OK")
    return 0


def grok_smoke() -> int:
    msg = f"Reply with only {SMOKE_TOKEN}"
    if grok_send_text(msg) != 0:
        log("=== BROCCOLI_DONE === grok FAIL: send")
        return 1
    log("STEP grok_smoke poll")
    for _ in range(40):
        xml = dump_ui()
        if _smoke_ok(xml):
            print(SMOKE_TOKEN)
            log("=== BROCCOLI_DONE === grok OK")
            return 0
        time.sleep(3)
    reply = _extract_assistant_reply(xml, user_prompt=msg)
    if reply and SMOKE_TOKEN in reply:
        print(SMOKE_TOKEN)
        log("=== BROCCOLI_DONE === grok OK")
        return 0
    log("=== BROCCOLI_DONE === grok FAIL:", reply or "no token")
    return 1


def grok_recon() -> int:
    launch_grok()
    xml = dump_ui()
    nodes = parse_nodes(xml)
    log("nodes", len(nodes))
    for n in nodes:
        if n.package != PKG:
            continue
        if n.text or n.resource_id or n.content_desc:
            log(
                " ",
                (n.resource_id or "-")[:40],
                (n.text or n.content_desc or "")[:60],
                n.bounds,
                "click" if n.clickable else "",
            )
    return 0


def grok_dump() -> int:
    launch_grok()
    xml = dump_ui()
    if not xml:
        return 1
    # stdout for pipes; full file on disk
    print(xml)
    return 0


def health() -> int:
    ok = True
    _, o, _ = rish_cmd("id")
    log("rish id:", (o or "").strip()[:120])
    if "uid=" not in (o or ""):
        ok = False
    _, o2, _ = rish_cmd(f"pm path {PKG}")
    if PKG not in (o2 or ""):
        log("WARN grok not installed?")
        ok = False
    log("DUMP_SD", DUMP_SD)
    log("health", "OK" if ok else "FAIL")
    return 0 if ok else 1


def run_task_line(line: str) -> int:
    line = line.strip()
    if not line or line.startswith("#"):
        return 0
    parts = line.split("|", 1)
    cmd = parts[0].strip().upper()
    arg = parts[1].strip() if len(parts) > 1 else ""
    if cmd == "SMOKE":
        return grok_smoke()
    if cmd == "DUMP":
        return grok_dump()
    if cmd == "SEND":
        return 0 if grok_send_text(arg or "ping") == 0 else 1
    if cmd == "ASK":
        return grok_ask(arg or "Say hello in one short sentence.")
    if cmd == "FILL_TEST":
        return grok_fill_test()
    log("unknown task", line)
    return 1


def run_once() -> int:
    if not QUEUE.is_file():
        log("no queue", QUEUE)
        return 0
    lines = QUEUE.read_text(encoding="utf-8", errors="replace").splitlines()
    todo = [ln for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    if not todo:
        return 0
    first, rest = todo[0], todo[1:]
    log("TASK", first)
    rc = run_task_line(first)
    remaining = [ln for ln in lines if ln.strip() != first.strip()]
    # remove only first matching pending task
    new_lines = []
    skipped = False
    for ln in lines:
        if not skipped and ln.strip() == first.strip() and ln.strip() and not ln.strip().startswith("#"):
            skipped = True
            continue
        new_lines.append(ln)
    QUEUE.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")
    META.mkdir(parents=True, exist_ok=True)
    (META / "last_task.json").write_text(
        json.dumps({"task": first, "rc": rc, "ts": time.time()}, indent=2),
        encoding="utf-8",
    )
    return rc


def watch(interval: int = 5) -> int:
    log("watch queue", QUEUE, "every", interval, "s")
    while True:
        try:
            if QUEUE.is_file():
                todo = [
                    ln
                    for ln in QUEUE.read_text(encoding="utf-8", errors="replace").splitlines()
                    if ln.strip() and not ln.strip().startswith("#")
                ]
                if todo:
                    run_once()
            time.sleep(interval)
        except KeyboardInterrupt:
            log("watch stop")
            return 0


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    if not args:
        log(
            "health | launch-grok | grok-dump | grok-recon | grok-fill-test | "
            "grok-send TEXT | grok-ask TEXT | grok-smoke | run-once | watch"
        )
        return 2
    a = args[0]
    if a == "health":
        return health()
    if a == "launch-grok":
        launch_grok()
        return 0
    if a == "grok-dump":
        return grok_dump()
    if a == "grok-recon":
        return grok_recon()
    if a == "grok-fill-test":
        return grok_fill_test()
    if a == "grok-send":
        msg = " ".join(args[1:]) or "ping"
        return 0 if grok_send_text(msg) == 0 else 1
    if a == "grok-ask":
        msg = " ".join(args[1:]) or "Say hello in one sentence."
        return grok_ask(msg)
    if a == "grok-smoke":
        return grok_smoke()
    if a == "run-once":
        return run_once()
    if a == "watch":
        sec = int(args[1]) if len(args) > 1 else 5
        return watch(sec)
    log("unknown", a)
    return 2



    if len(sys.argv) > 1 and sys.argv[1] in ("show-queue", "show_queue", "queue"):
        import subprocess
        subprocess.run(["bash", str(Path.home() / "broccoli/tools/show_queue.sh")], check=False)
        raise SystemExit(0)


if __name__ == "__main__" and len(sys.argv) > 1:
    _cmd = sys.argv[1]
    if _cmd in ("show-queue", "show_queue", "queue"):
        import subprocess
        subprocess.run(["bash", str(Path.home() / "broccoli/tools/show_queue.sh")], check=False)
        raise SystemExit(0)
    if _cmd in ("wire-dump", "ui-dump"):
        import subprocess
        subprocess.run(["bash", str(Path.home() / "broccoli/lib/ui_dump_rish.sh")], check=False)
        subprocess.run(["python3", str(Path.home() / "broccoli/tools/ui_dump_chat.py"), "report"], check=False)
        raise SystemExit(0)
    if _cmd in ("start-dev", "start", "wire-once"):
        import subprocess
        subprocess.run(["bash", str(Path.home() / "broccoli/tools/wire_loop_full.sh"), "once"], check=False)
        raise SystemExit(0)



def grok_paste_send(body: str) -> bool:
    launch_grok()
    time.sleep(2)
    if not paste_to_composer(body):
        return False
    send_tap()
    time.sleep(1)
    return True
if __name__ == "__main__":
    raise SystemExit(main())


def clipboard_set(text, toast=True):
    import subprocess as _sp
    t = (text or "")[:50000]
    r = _sp.run(["termux-clipboard-set"], input=t.encode("utf-8"), capture_output=True, timeout=15)
    if r.returncode != 0:
        log("clipboard_set FAIL", r.stderr[:200])
        return False
    if toast:
        _sp.run(["termux-toast", "-s", "Broccoli: prompt on clipboard"], timeout=5, check=False)
    log("clipboard_set ok", len(t))
    return True

def clipboard_get():
    import subprocess as _sp
    r = _sp.run(["termux-clipboard-get"], capture_output=True, text=True, timeout=8)
    return (r.stdout or "").strip()

def clipboard_fingerprint(text):
    import hashlib
    t = (text or "")[:8000]
    return hashlib.sha256(t.encode("utf-8", errors="replace")).hexdigest()[:16]

def paste_to_composer(prompt):
    """Set clipboard to prompt, verify, then paste into composer."""
    import time as _t
    prompt = (prompt or "").strip()
    if not prompt:
        log("paste_to_composer empty")
        return False
    fp_want = clipboard_fingerprint(prompt)
    if not clipboard_set(prompt, toast=True):
        return False
    _t.sleep(0.35)
    got = clipboard_get()
    fp_got = clipboard_fingerprint(got)
    if fp_got != fp_want and got[:200] != prompt[:200]:
        import subprocess as _sp
        _sp.run(["termux-toast", "-s", "Broccoli: clipboard mismatch — fix before send"], timeout=5, check=False)
        log("clipboard MISMATCH", fp_want, fp_got, repr(got[:80]))
        return False
    # focus composer tap if cal exists
    try:
        import json
        cal = json.loads((Path.home() / ".grok_ui_cal.json").read_text())
        cx, cy = cal.get("composer", [540, 2200])
        shizuku_cmd("input tap %d %d" % (int(cx), int(cy)))
        _t.sleep(0.25)
    except Exception:
        pass
    shizuku_cmd("input keyevent 279")  # PASTE
    _t.sleep(0.4)
    log("paste_to_composer done", len(prompt))
    return True

# CLI hook
import sys as _sys_gps
if __name__ == "__main__" and len(_sys_gps.argv) > 1 and _sys_gps.argv[1] == "grok-paste-send":
    _b = _sys_gps.stdin.read() if not _sys_gps.stdin.isatty() else " ".join(_sys_gps.argv[2:])
    _sys_gps.exit(0 if grok_paste_send(_b) else 1)
