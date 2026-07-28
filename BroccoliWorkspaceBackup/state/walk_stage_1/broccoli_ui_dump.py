import os, re, time, xml.etree.ElementTree as ET
from pathlib import Path
from broccoli_rish_shell import shell, rish_path, wm_size

BRO = Path.home() / "broccoli"
UI = Path(os.environ.get("BROCCOLI_UI_DUMP", str(BRO / "ui")))

def ui_dump(remote=None):
    UI.mkdir(parents=True, exist_ok=True)
    remote = remote or str(UI / "window_dump.xml")
    cmds = []
    if rish_path():
        cmds.append(f"uiautomator dump --compressed {remote} 2>/dev/null; cat {remote}")
    cmds += [
        f"uiautomator dump --compressed {remote} 2>/dev/null; cat {remote}",
        f"cmd uiautomator dump {remote} 2>/dev/null; cat {remote}",
    ]
    xml = ""
    for c in cmds:
        rc, out = shell(c, timeout=16)
        if "<?xml" in out:
            xml = out[out.find("<?xml"):]
            break
        time.sleep(0.04)
    if len(xml) > 80:
        (UI / "last_dump.xml").write_text(xml[:2_000_000], encoding="utf-8")
    return xml

def _bounds(b):
    m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", b or "")
    if not m: return None
    x1,y1,x2,y2 = map(int, m.groups())
    return dict(x1=x1,y1=y1,x2=x2,y2=y2,cx=(x1+x2)//2,cy=(y1+y2)//2)

def nodes(xml):
    if not xml or "<?xml" not in xml: return []
    try:
        root = ET.fromstring(xml.encode("utf-8", errors="replace"))
    except ET.ParseError:
        return []
    out = []
    for el in root.iter("node"):
        b = _bounds(el.get("bounds"))
        if not b: continue
        out.append({
            "text": (el.get("text") or "").strip(),
            "desc": (el.get("content-desc") or "").strip(),
            "rid": el.get("resource-id") or "",
            "cls": el.get("class") or "",
            "pkg": el.get("package") or "",
            "clickable": el.get("clickable") == "true",
            "focusable": el.get("focusable") == "true",
            **b,
        })
    return out

def find_grok_search_box(ns, pkg=None):
    if not ns: return None
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    _, h = wm_size()
    pool = [n for n in ns if pkg in (n.get("pkg") or "")] or ns
    def sc(n):
        blob = (n.get("text","")+n.get("desc","")+n.get("rid","")).lower()
        s = 0
        if "EditText" in n.get("cls",""): s += 50
        if n.get("focusable"): s += 12
        for k in ("ask","search","message","prompt","compose","anything"):
            if k in blob: s += 10
        if n.get("cy",0) >= h*0.65: s += 20
        return s
    cands = [n for n in pool if sc(n) > 15 or "EditText" in n.get("cls","")]
    if not cands:
        cands = [n for n in pool if n.get("clickable") and n.get("cy",0) >= h*0.72]
    return max(cands, key=sc) if cands else None

find_composer = find_grok_search_box

def find_all_send_candidates(ns, pkg=None):
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    _, h = wm_size()
    out = []
    for n in ns:
        if pkg not in (n.get("pkg") or ""): continue
        blob = (n["text"]+" "+n["desc"]+" "+n["rid"]).lower()
        if not n["clickable"]: continue
        score = 0
        if any(k in blob for k in ("send", "submit", "post", "arrow", "go", "done")): score += 50
        if "ImageButton" in n["cls"] or "Button" in n["cls"] or "FloatingActionButton" in n["cls"]: score += 15
        if n["cy"] >= h * 0.55: score += 10
        if "send" in n["rid"].lower(): score += 40
        if score > 0 or ("Image" in n["cls"] and n["cy"] > h*0.6):
            out.append((score, n))
    out.sort(key=lambda x: -x[0])
    return [n for _, n in out]

def find_send(ns, pkg=None):
    c = find_all_send_candidates(ns, pkg)
    return c[0] if c else None

def composer_has_text(ns, comp, needle):
    if not comp or not needle: return False
    needle = needle.strip()
    parts = [comp.get("text") or "", comp.get("desc") or ""]
    for n in ns:
        if n.get("text") and abs(n["cy"]-comp["cy"]) < 90:
            parts.append(n["text"])
    blob = " ".join(parts)
    if needle in blob: return True
    return needle[:18] in blob or (len(needle) > 8 and needle[:10] in blob)

def last_reply_text(ns, pkg=None):
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    skip = ("ask anything", "search", "send", "menu", "settings", "attach", "voice", "new chat", "grok")
    msgs = []
    for n in ns:
        if pkg and pkg not in (n.get("pkg") or ""): continue
        t = n.get("text") or ""
        if len(t) < 3 or "EditText" in n.get("cls",""): continue
        if any(s in t.lower() for s in skip) and len(t) < 50: continue
        msgs.append(n)
    msgs.sort(key=lambda n: n["cy"])
    return msgs[-1]["text"] if msgs else ""

def dump_debug_summary(ns, pkg=None):
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    sends = find_all_send_candidates(ns, pkg)
    box = find_grok_search_box(ns, pkg)
    return {
        "nodes": len(ns),
        "box": {k: box.get(k) for k in ("cx","cy","text","desc","rid","cls")} if box else None,
        "sends": [{k: s.get(k) for k in ("cx","cy","text","desc","rid","cls")} for s in sends[:5]],
    }
