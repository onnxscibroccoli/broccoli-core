#!/usr/bin/env python3
"""Find composer + send in UI XML; paste via clipboard; tap send via rish."""
import re, subprocess, sys, time
from pathlib import Path

HOME = Path.home()
PKG = "ai.x.grok"  # adjust if Grok is native app
RISH = "rish"

def rish_lines(cmds, timeout=45):
    script = "\n".join(cmds) + "\n"
    p = subprocess.run([RISH], input=script, capture_output=True, text=True, timeout=timeout, errors="replace")
    return (p.stdout or "") + (p.stderr or "")

def rish_shell(cmd, timeout=30):
    return rish_lines([f"shell {cmd}"], timeout=timeout)

def dump_xml():
    for path in ("/data/local/tmp/broccoli_ui.xml", "/sdcard/broccoli_ui.xml"):
        rish_shell(f"uiautomator dump --compressed {path}")
        out = rish_shell(f"wc -c {path}")
        m = re.search(r"(\d+)\s+" + re.escape(path), out)
        if m and int(m.group(1)) > 3000:
            # read via rish cat in chunks - use pull from termux if readable
            local = HOME / "broccoli/ui/last_ui.xml"
            try:
                subprocess.run(["cp", path, str(local)], check=False, timeout=5)
            except Exception:
                pass
            if local.is_file() and local.stat().st_size > 3000:
                return local.read_text(encoding="utf-8", errors="replace")
    for p in (HOME/"broccoli/ui/last_ui.xml", HOME/"broccoli/ui/last.xml"):
        if p.is_file() and p.stat().st_size > 3000:
            return p.read_text(encoding="utf-8", errors="replace")
    return ""

def bounds_center(b):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
    if not m:
        return None
    x1,y1,x2,y2 = map(int, m.groups())
    return (x1+x2)//2, (y1+y2)//2

def parse_nodes(xml):
    nodes = []
    for m in re.finditer(r'<node([^>]+)>', xml):
        attrs = m.group(1)
        def attr(name):
            mm = re.search(rf'{name}="([^"]*)"', attrs)
            return mm.group(1) if mm else ""
        nodes.append({
            "klass": attr("class"),
            "text": attr("text"),
            "desc": attr("content-desc"),
            "rid": attr("resource-id"),
            "bounds": attr("bounds"),
            "clickable": attr("clickable") == "true",
            "pkg": attr("package"),
        })
    return nodes

def find_composer(nodes):
    for n in nodes:
        if "chat_text_input" in n["rid"]:
            return n
    for n in nodes:
        if "EditText" in n["klass"] and ("grok" in n["pkg"].lower() or "chrome" in n["pkg"].lower() or n["pkg"]):
            return n
    for n in nodes:
        t = (n["text"] + n["desc"]).lower()
        if "ask" in t and ("grok" in t or "anything" in t or "message" in t):
            return n
    return None

def find_send(nodes, composer_cy=None):
    keywords = re.compile(r"send|submit|post|arrow|voice", re.I)
    best = None
    for n in nodes:
        blob = " ".join([n["desc"], n["rid"], n["klass"], n["text"]])
        if not keywords.search(blob):
            continue
        if "EditText" in n["klass"]:
            continue
        c = bounds_center(n["bounds"])
        if not c:
            continue
        cy = c[1]
        if composer_cy is not None and cy < composer_cy - 80:
            continue
        if n["clickable"] or "Button" in n["klass"] or "ImageButton" in n["klass"]:
            best = (c[0], c[1], blob[:80])
            break
    if best:
        return best
    # fallback: right side of screen near bottom (Grok send often bottom-right)
    return None

def clipboard_set(text):
    subprocess.run(["termux-clipboard-set"], input=text.encode("utf-8"), check=False, timeout=20)
    esc = text.replace("\\", "\\\\").replace('"', '\\"')[:8000]
    rish_shell(f'cmd clipboard set "{esc}"')

def tap(x, y):
    rish_shell(f"input tap {x} {y}")

def paste_keyevents():
    rish_shell("input keyevent 279")  # PASTE
    time.sleep(0.3)

def send_enter():
    rish_shell("input keyevent 66")  # ENTER
    time.sleep(0.2)

def compose_and_send(message, do_launch=True):
    if do_launch:
        subprocess.run(["am", "start", "-a", "android.intent.action.VIEW",
                        "-d", "", "-p", "ai.x.grok"], check=False, timeout=15)
        time.sleep(4)
    xml = dump_xml()
    if not xml or "<hierarchy" not in xml:
        return 1, "no_xml"
    nodes = parse_nodes(xml)
    comp = find_composer(nodes)
    if not comp:
        return 2, "no_composer"
    cc = bounds_center(comp["bounds"])
    if not cc:
        return 3, "bad_composer_bounds"
    tap(cc[0], cc[1])
    time.sleep(0.5)
    clipboard_set(message)
    paste_keyevents()
    time.sleep(0.8)
    xml2 = dump_xml()
    nodes2 = parse_nodes(xml2) if xml2 else nodes
    comp_cy = cc[1]
    send = find_send(nodes2, composer_cy=comp_cy)
    if send:
        tap(send[0], send[1])
        return 0, f"sent_tap {send[2]}"
    send_enter()
    return 0, "sent_enter_fallback"

if __name__ == "__main__":
    msg = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    if not msg.strip():
        print("usage: grok_send_tap.py MESSAGE", file=sys.stderr)
        sys.exit(2)
    rc, why = compose_and_send(msg.strip())
    print(why)
    sys.exit(rc)
