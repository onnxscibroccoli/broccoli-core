#!/usr/bin/env python3
"""Extract visible chat lines from accessibility dump (+ optional scroll)."""
import os, re, subprocess
from xml.etree import ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DUMP = "/sdcard/broccoli_window_dump.xml"

SKIP = re.compile(
    r"^(ask anything|send|listen|stop|grok|menu|new chat|\.{1,3})$", re.I
)

def scroll_end():
    for script in ("scripts/scroll_chat_end.py", "scroll_chat_end.py"):
        p = os.path.join(ROOT, script)
        if os.path.isfile(p):
            try:
                subprocess.run(["python3", p], cwd=ROOT, timeout=45, capture_output=True)
            except Exception:
                pass
            return True
    # fallback: swipe up on chat area
    try:
        subprocess.run(["bash", "lib/rish_cmd.sh", "input swipe 540 1600 540 600 400"],
                       cwd=ROOT, timeout=8, capture_output=True)
    except Exception:
        pass
    return False

def texts_from_xml(xml: str) -> list[str]:
    out = []
    try:
        root = ET.fromstring(xml)
    except Exception:
        # regex fallback
        for m in re.finditer(r'text="([^"]{2,})"', xml):
            t = m.group(1).strip()
            if t and not SKIP.match(t):
                out.append(t)
        return out
    for node in root.iter("node"):
        t = (node.get("text") or "").strip()
        if len(t) < 2 or SKIP.match(t):
            continue
        out.append(t)
    # de-dupe consecutive
    dedup = []
    for t in out:
        if not dedup or dedup[-1] != t:
            dedup.append(t)
    return dedup

def read_thread(*, scroll=True) -> dict:
    if scroll:
        scroll_end()
        try:
            subprocess.run(["bash", "ui_snapshot.sh"], cwd=ROOT, timeout=22, capture_output=True)
        except Exception:
            pass
    try:
        xml = open(DUMP, encoding="utf-8", errors="ignore").read()
    except Exception:
        xml = ""
    lines = texts_from_xml(xml)
    # heuristic: last chunk often assistant; keep full transcript
    return {
        "lines": lines,
        "line_count": len(lines),
        "tail": "\n".join(lines[-24:]) if lines else "",
        "last_line": lines[-1] if lines else "",
    }

def precondition(state: dict) -> tuple[bool, str]:
    if not state.get("in_grok_chat"):
        return False, "not_in_grok"
    if state.get("new_chat_focused"):
        return False, "new_chat_focused"
    return True, "ok"

def run(ctx) -> "ModuleResult":
    from modules.registry import ModuleResult
    from modules.state_probe import snap
    snap()
    data = read_thread(scroll=os.environ.get("BROCC_NO_SCROLL") != "1")
    cap = os.path.join(ctx.root, "ui", "last_capture.txt")
    open(cap, "w", encoding="utf-8").write(data["tail"] + "\n")
    return ModuleResult(True, "chat_reader", data=data)
