#!/usr/bin/env python3
"""
PARAMOUNT: open Grok ASK CHAT in foreground (not Imagine, not background).
Steps: launch → dump UI → tap Ask → tap/focus chat_text_input → scroll_chat_end → heal.
"""
import re, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
ROOT = HOME / "broccoli"
BOOT = HOME / "broccoli_bootstrap.py"
UI = ROOT / "ui"
PKG = "ai.x.grok"

def run(cmd, t=90):
    print("CHAT_FG", cmd[:200], flush=True)
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    except Exception as e:
        print("CHAT_FG ERR", e, flush=True)
        return type("R", (), {"stdout": "", "stderr": str(e), "returncode": -1})()

def toast(msg):
    subprocess.run(["termux-toast", "-g", "center", msg[:120]], timeout=8, capture_output=True)
    print("TOAST", msg, flush=True)

def save_xml_from_output(raw):
    if "<?xml" not in raw and "<hierarchy" not in raw:
        return ""
    i = raw.find("<?xml")
    if i < 0:
        i = raw.find("<hierarchy")
    j = raw.rfind("</hierarchy>")
    if j > i:
        xml = raw[i : j + 12]
        (UI / "last_ui.xml").write_text(xml, errors="replace")
        return xml
    return ""

def bounds_center(bounds):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
    if not m:
        return None
    a, b, c, d = map(int, m.groups())
    return (a + c) // 2, (b + d) // 2

def find_in_xml(xml, **kw):
    """kw: resource_id=, text=, content_desc=, class_contains="""
    nodes = []
    for chunk in re.split(r"(?=<node )", xml):
        ok = True
        for k, v in kw.items():
            if k == "resource_id" and f'resource-id="{v}"' not in chunk:
                ok = False
            elif k == "text" and f'text="{v}"' not in chunk:
                ok = False
            elif k == "content_desc" and f'content-desc="{v}"' not in chunk:
                ok = False
            elif k == "class_contains" and v not in chunk:
                ok = False
        if not ok:
            continue
        bm = re.search(r'bounds="(\[[^\]]+\]\[[^\]]+\])"', chunk)
        if bm:
            nodes.append((chunk, bm.group(1)))
    return nodes

def dump_ui():
    if not Path(BOOT).exists():
        return ""
    r = run(f'python3 "{BOOT}" dump_ui', 70)
    raw = (r.stdout or "") + (r.stderr or "")
    return save_xml_from_output(raw) or (UI / "last_ui.xml").read_text(errors="replace") if (UI / "last_ui.xml").exists() else ""

def tap_xy(x, y):
    run(f'python3 "{BOOT}" tap {x} {y}', 20)

def launch_grok():
    toast("Open Grok chat…")
    run(f'python3 "{BOOT}" launch_grok', 50)
    time.sleep(2)
    if "grok" not in (run('dumpsys window windows 2>/dev/null | grep -i focus | head -2', 12).stdout or "").lower():
        run(f"monkey -p {PKG} -c android.intent.category.LAUNCHER 1", 25)
        time.sleep(2.5)

def ensure_ask_chat(xml):
    """Imagine tab steals chat — tap Ask."""
    hits = find_in_xml(xml, text="Ask")
    for _, b in hits:
        c = bounds_center(b)
        if c and c[1] < 400:
            toast("Tap Ask")
            tap_xy(*c)
            time.sleep(1.2)
            return True
    hits = find_in_xml(xml, content_desc="Ask")
    for _, b in hits:
        c = bounds_center(b)
        if c:
            tap_xy(*c)
            time.sleep(1.2)
            return True
    return False

def focus_composer(xml):
    """chat_text_input = real chat foreground."""
    for rid in ("chat_text_input",):
        hits = find_in_xml(xml, resource_id=rid)
        for _, b in hits:
            c = bounds_center(b)
            if c:
                toast("Focus chat")
                tap_xy(*c)
                time.sleep(0.8)
                return True
    hits = find_in_xml(xml, text="Ask anything")
    for _, b in hits:
        c = bounds_center(b)
        if c and c[1] > 1500:
            tap_xy(*c)
            time.sleep(0.8)
            return True
    return False

def scroll_chat_end():
    if Path(BOOT).exists():
        run(f'python3 "{BOOT}" scroll_chat_end', 35)

def main():
    sys.path.insert(0, str(ROOT / "lib"))
    from display_context import log_display
    log_display(ROOT / "reports/display_at_chat_fg.json")

    if not Path(BOOT).exists():
        toast("No bootstrap")
        return 1

    launch_grok()
    xml = dump_ui()
    if not xml or "ai.x.grok" not in xml:
        toast("Grok UI dump failed")
        return 1

    ensure_ask_chat(xml)
    xml = dump_ui() or xml
    if not focus_composer(xml):
        toast("No composer — retry dump")
        xml = dump_ui()
        focus_composer(xml or "")

    scroll_chat_end()
    time.sleep(0.5)
    dump_ui()

    toast("Chat foreground OK — heal")
    run(f'python3 "{ROOT}/broccoli_meta_heal.py"', 100)
    run(f'python3 "{ROOT}/workflow_front.py"', 120)

    xml2 = dump_ui()
    ok = bool(xml2 and ("chat_text_input" in xml2 or "Ask anything" in xml2))
    log_display(ROOT / "reports/display_after_chat_fg.json")
    toast("Chat FG + heal done" if ok else "Check Grok on screen")
    return 0 if ok else 2

if __name__ == "__main__":
    sys.exit(main())
