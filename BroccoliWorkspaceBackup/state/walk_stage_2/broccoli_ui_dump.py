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
        rc, out = shell(c, timeout=18)
        if "<?xml" in out:
            xml = out[out.find("<?xml"):]
            break
        time.sleep(0.05)
    if len(xml) > 100:
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

def _score_grok_input(n, h):
    """Grok home: search / ask bar (often placeholder, not filled text)."""
    blob = (n.get("text","") + " " + n.get("desc","") + " " + n.get("rid","")).lower()
    sc = 0
    if "EditText" in n.get("cls",""): sc += 40
    if n.get("focusable"): sc += 15
    if n.get("clickable"): sc += 8
    for k in ("ask", "search", "message", "prompt", "compose", "query", "grok", "anything", "type"):
        if k in blob: sc += 12
    for k in ("input", "composer", "search", "ask", "chat", "edit"):
        if k in blob: sc += 6
    # prefer bottom bar (composer / search on home)
    cy = n.get("cy", 0)
    if cy >= h * 0.65: sc += 25
    if cy >= h * 0.78: sc += 15
    return sc

def find_grok_search_box(ns, pkg=None):
    if not ns: return None
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    _, h = wm_size()
    in_pkg = [n for n in ns if pkg in (n.get("pkg") or "")]
    pool = in_pkg if in_pkg else ns
    candidates = [n for n in pool if "EditText" in n.get("cls","") or n.get("focusable") or
                  any(k in (n.get("desc","")+n.get("text","")+n.get("rid","")).lower()
                      for k in ("ask","search","message","compose"))]
    if not candidates:
        candidates = [n for n in pool if n.get("clickable") and n.get("cy",0) >= h*0.7]
    if not candidates:
        return None
    return max(candidates, key=lambda n: _score_grok_input(n, h))

find_composer = find_grok_search_box

def find_send(ns, pkg=None):
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    for n in ns:
        if pkg not in (n.get("pkg") or ""): continue
        blob = (n["text"]+" "+n["desc"]+" "+n["rid"]).lower()
        if n["clickable"] and any(k in blob for k in ("send", "submit", "post", "arrow", "go")):
            return n
    clicks = [n for n in ns if n["clickable"] and ("Button" in n["cls"] or "Image" in n["cls"])]
    return max(clicks, key=lambda n: n["cy"]) if clicks else None

def composer_has_text(ns, comp, needle):
    if not comp: return False
    needle = (needle or "").strip()
    chunks = [comp.get("text") or "", comp.get("desc") or ""]
    x1, y1, x2, y2 = comp["x1"], comp["y1"], comp["x2"], comp["y2"]
    for n in ns:
        if n.get("text") and abs(n["cy"]-comp["cy"]) < 100 and n["x1"] >= x1 - 40:
            chunks.append(n["text"])
    blob = " ".join(chunks)
    if needle[:20] in blob: return True
    if len(blob) >= max(10, len(needle)//3) and needle[:10] in blob: return True
    return False

def last_reply_text(ns, pkg=None):
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    skip = ("ask anything", "search", "send", "menu", "settings", "attach", "voice", "new chat")
    msgs = []
    for n in ns:
        if pkg and pkg not in (n.get("pkg") or ""): continue
        t = n.get("text") or ""
        if len(t) < 4 or "EditText" in n.get("cls",""): continue
        low = t.lower()
        if any(s in low for s in skip) and len(t) < 45: continue
        msgs.append(n)
    msgs.sort(key=lambda n: n["cy"])
    return msgs[-1]["text"] if msgs else ""
