#!/usr/bin/env python3
"""All waits derive from UI dump state — not wall-clock guesses."""
import hashlib, json, re, sys
from pathlib import Path

HOME = Path.home()
XML = HOME / "broccoli/ui/last_ui.xml"
GROK = "ai.x.grok"
NOISE = re.compile(r"^(Ask|Send|Grok|Imagine|Explore|Home|Menu|Search|Voice|New chat|\s*)$", re.I)

def load_xml():
    if not XML.is_file() or XML.stat().st_size < 400:
        return ""
    return XML.read_text(encoding="utf-8", errors="replace")

def nodes(xml):
    out = []
    for m in re.finditer(r"<node([^>]+)/?>", xml):
        a = m.group(1)
        def g(k):
            mm = re.search(rf'{k}="([^"]*)"', a)
            return mm.group(1) if mm else ""
        out.append({
            "text": g("text"), "desc": g("content-desc"), "rid": g("resource-id"),
            "klass": g("class"), "pkg": g("package"), "bounds": g("bounds"),
            "clickable": g("clickable") == "true",
        })
    return out

def fingerprint(xml):
    if not xml:
        return "empty"
    lines = []
    for n in nodes(xml):
        for f in ("text", "desc"):
            t = (n[f] or "").strip()
            if len(t) >= 2 and not NOISE.match(t):
                lines.append(t)
    blob = "\n".join(lines[-30:])
    return hashlib.md5(blob.encode("utf-8", errors="replace")).hexdigest()

def chat_lines(xml):
    lines, seen = [], set()
    for n in nodes(xml):
        for f in ("text", "desc"):
            t = (n[f] or "").strip()
            if len(t) < 2 or len(t) > 6000 or NOISE.match(t):
                continue
            if t in seen:
                continue
            seen.add(t)
            lines.append(t)
    return lines

def composer(xml):
    for n in nodes(xml):
        if "chat_text_input" in n["rid"] and n["bounds"]:
            return n
    for n in nodes(xml):
        if "EditText" in n["klass"] and GROK in n["pkg"] and n["bounds"]:
            return n
    for n in nodes(xml):
        if "EditText" in n["klass"] and n["bounds"]:
            return n
    return None

def send_btn(xml, composer_bounds):
    if not composer_bounds:
        return None
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", composer_bounds)
    if not m:
        return None
    cy = (int(m.group(2)) + int(m.group(4))) // 2
    best = None
    for n in nodes(xml):
        if not n["clickable"] or not n["bounds"]:
            continue
        blob = " ".join([n["desc"], n["rid"], n["klass"], n["text"]])
        if not re.search(r"send|submit|ImageButton", blob, re.I):
            continue
        bm = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", n["bounds"])
        if not bm:
            continue
        by = (int(bm.group(2)) + int(bm.group(4))) // 2
        if by < cy - 60:
            continue
        best = n
    return best

def ask_tab(xml):
    for n in nodes(xml):
        if (n["text"] or "").strip().lower() == "ask" and n["bounds"]:
            return n
    return None

def composer_has_text(xml, needle):
    if not needle or len(needle) < 4:
        return False
    frag = needle[: min(40, len(needle))]
    for n in nodes(xml):
        if "EditText" in n["klass"] or "chat_text_input" in n["rid"]:
            t = (n["text"] or "") + (n["desc"] or "")
            if frag in t:
                return True
    if frag in xml:
        return True
    return False

def state(msg_to_send=""):
    xml = load_xml()
    lines = chat_lines(xml)
    comp = composer(xml)
    return {
        "bytes": len(xml),
        "grok_fg": GROK in xml,
        "fp": fingerprint(xml),
        "last_line": lines[-1] if lines else "",
        "lines_tail": lines[-8:],
        "has_composer": comp is not None,
        "composer_bounds": comp["bounds"] if comp else "",
        "has_send": send_btn(xml, comp["bounds"] if comp else "") is not None,
        "has_ask_tab": ask_tab(xml) is not None,
        "composer_has_msg": composer_has_text(xml, msg_to_send),
        "msg_in_chat": msg_to_send and any(msg_to_send[:30] in ln for ln in lines[-6:]),
    }

def tap_center(bounds):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
    if not m:
        return None
    x1,y1,x2,y2 = map(int, m.groups())
    return (x1+x2)//2, (y1+y2)//2

def cmd_tap(x, y):
    print(f"RISH input tap {x} {y}")

def plan_actions(msg=""):
    xml = load_xml()
    s = state(msg)
    actions = []
    if not s["grok_fg"]:
        actions.append(("launch", "grok"))
    if s["grok_fg"] and not s["has_composer"] and s["has_ask_tab"]:
        n = ask_tab(xml)
        if n:
            xy = tap_center(n["bounds"])
            if xy:
                actions.append(("tap", xy[0], xy[1], "ask"))
    comp = composer(xml)
    if comp and msg and not s["composer_has_msg"]:
        xy = tap_center(comp["bounds"])
        if xy:
            actions.append(("tap", xy[0], xy[1], "composer"))
        actions.append(("paste", msg))
    if comp and msg:
        sb = send_btn(xml, comp["bounds"])
        if sb:
            xy = tap_center(sb["bounds"])
            if xy:
                actions.append(("tap", xy[0], xy[1], "send"))
        else:
            actions.append(("key", 66, "enter"))
    return actions

if __name__ == "__main__":
    op = sys.argv[1] if len(sys.argv) > 1 else "state"
    if op == "state":
        m = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(state(m), indent=2, ensure_ascii=False))
    elif op == "fp":
        print(fingerprint(load_xml()))
    elif op == "last":
        print(state()["last_line"])
    elif op == "plan":
        msg = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(plan_actions(msg), ensure_ascii=False))
    elif op == "lines":
        for ln in state()["lines_tail"]:
            print(ln)
