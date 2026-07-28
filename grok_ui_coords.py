#!/usr/bin/env python3
import json, re, xml.etree.ElementTree as ET
from pathlib import Path
B = Path(__import__("os").environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
PKG = "ai.x.grok"
BLOCK = ("voice", "grok voice", "images selector", "new chat", "imagine")

def bds(s):
    m = list(map(int, re.findall(r"\d+", s or "")))
    return (m[0], m[1], m[2], m[3]) if len(m) >= 4 else None

root = ET.parse(B/"window_dump.xml").getroot()
inp, send, ask = None, None, False
cands = []
for el in root.iter("node"):
    if PKG not in (el.attrib.get("package") or PKG): continue
    rid = el.attrib.get("resource-id") or ""
    if "chat_text_input" in rid:
        b = bds(el.attrib.get("bounds",""))
        if b: inp = {"x":(b[0]+b[2])//2,"y":(b[1]+b[3])//2}
    if (el.attrib.get("text") or "") == "Ask anything": ask = True
    if el.attrib.get("clickable") != "true": continue
    b = bds(el.attrib.get("bounds",""))
    if not b: continue
    cx, cy = (b[0]+b[2])//2, (b[1]+b[3])//2
    w, h = b[2]-b[0], b[3]-b[1]
    if cy < 2000: continue
    lab = (el.attrib.get("text") or el.attrib.get("content-desc") or "")
    low = lab.lower()
    if any(x in low for x in BLOCK): continue
    sc = cy
    if "send" in low: sc += 10000
    elif not ask and w <= 240 and h <= 240 and cx >= 820: sc += 5000
    else: continue
    cands.append((sc, cx, cy, lab))
if cands:
    cands.sort(reverse=True)
    _, x, y, lab = cands[0]
    send = {"x": x, "y": y, "label": lab}
print(json.dumps({"ok": True, "phase": "empty" if ask else "filled", "composer_empty_hint": ask, "input": inp, "send": send}, indent=2))
