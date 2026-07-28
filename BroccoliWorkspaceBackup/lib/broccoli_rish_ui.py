"""Rish-only UI: dump a11y tree -> tap node bounds. No APK."""
import os, re, time, json, xml.etree.ElementTree as ET
from pathlib import Path
from broccoli_rish_shell import shell

GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
BRO = Path.home() / "broccoli"

def _bounds(b):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
    if not m: return None
    x1,y1,x2,y2 = map(int, m.groups())
    return x1,y1,x2,y2,(x1+x2)//2,(y1+y2)//2

def dump_xml():
    remote = "/data/local/tmp/ui.xml"
    for c in (
        f"uiautomator dump --compressed {remote} 2>/dev/null; cat {remote}",
        f"cmd uiautomator dump {remote} 2>/dev/null; cat {remote}",
    ):
        rc, out = shell(c, timeout=14)
        if "<?xml" in out:
            xml = out[out.find("<?xml"):]
            (BRO/"ui/last_dump.xml").write_text(xml[:1_500_000], encoding="utf-8")
            return xml
    return ""

def nodes(xml):
    if not xml: return []
    try:
        root = ET.fromstring(xml.encode("utf-8", errors="replace"))
    except ET.ParseError:
        return []
    out = []
    for el in root.iter("node"):
        b = _bounds(el.get("bounds"))
        if not b: continue
        x1,y1,x2,y2,cx,cy = b
        out.append({
            "text": (el.get("text") or "").strip(),
            "desc": (el.get("content-desc") or "").strip(),
            "rid": el.get("resource-id") or "",
            "cls": el.get("class") or "",
            "pkg": el.get("package") or "",
            "clickable": el.get("clickable") == "true",
            "focusable": el.get("focusable") == "true",
            "cx": cx, "cy": cy, "x1": x1, "y1": y1, "x2": x2, "y2": y2,
        })
    return out

def in_grok(n):
    return GROK in (n.get("pkg") or "")

def tap(cx, cy):
    shell(f"input tap {int(cx)} {int(cy)}")
    time.sleep(0.12)

def paste_clip():
    shell("input keyevent 279")
    time.sleep(0.12)

def enter():
    shell("input keyevent 66")
    time.sleep(0.2)

def find_composer(ns):
    pool = [n for n in ns if in_grok(n)] or ns
    best, sc = None, -1
    for n in pool:
        blob = (n["text"]+" "+n["desc"]+" "+n["rid"]).lower()
        s = 0
        if "edittext" in n["cls"].lower(): s += 60
        if n["focusable"]: s += 10
        for k in ("ask","search","message","compose","prompt"):
            if k in blob: s += 8
        s += n["cy"] // 40
        if s > sc: sc, best = s, n
    return best

def find_send(ns):
    pool = [n for n in ns if in_grok(n) and n["clickable"]] or [n for n in ns if n["clickable"]]
    ranked = []
    for n in pool:
        blob = (n["text"]+" "+n["desc"]+" "+n["rid"]).lower()
        s = 0
        if "send" in blob: s += 80
        if "submit" in blob or "post" in blob: s += 40
        if "send" in n["rid"].lower(): s += 70
        if "image" in n["cls"].lower() or "button" in n["cls"].lower(): s += 15
        s += n["cy"] // 50
        if s > 10: ranked.append((s, n))
    ranked.sort(key=lambda x: -x[0])
    return ranked[0][1] if ranked else None

def composer_text(ns, comp):
    if not comp: return ""
    parts = [comp.get("text") or "", comp.get("desc") or ""]
    for n in ns:
        if n.get("text") and abs(n["cy"]-comp["cy"]) < 100:
            parts.append(n["text"])
    return " ".join(parts)

def last_assistant(ns):
    skip = ("ask anything","search","send","menu","settings")
    msgs = []
    for n in ns:
        if not in_grok(n): continue
        t = n.get("text") or ""
        if len(t) < 4 or "edittext" in n["cls"].lower(): continue
        if any(s in t.lower() for s in skip) and len(t) < 40: continue
        msgs.append(n)
    msgs.sort(key=lambda n: n["cy"])
    return msgs[-1]["text"] if msgs else ""

def clip_set(text):
    import subprocess
    p = os.path.join(os.environ.get("PREFIX",""), "bin", "termux-clipboard-set")
    if os.path.isfile(p):
        subprocess.run([p, text], timeout=8)
        return True
    return False

def open_grok():
    shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
    time.sleep(0.35)

def send_task(task):
    """ADB sibling send only — no enter()."""
    import os
    os.environ.setdefault("BROCCOLI_NO_ENTER", "1")
    os.environ.setdefault("BROCCOLI_SEND_MODE", "sibling_only")
    from broccoli_core_round import full_round
    return full_round(task)
