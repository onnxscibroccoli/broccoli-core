#!/usr/bin/env python3
import json, re, sys, xml.etree.ElementTree as ET
from pathlib import Path
B = Path(__import__("os").environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
PKG = "ai.x.grok"
prof = json.loads((B/"chat_profile.json").read_text()) if (B/"chat_profile.json").is_file() else {}
PKG = prof.get("chat_package", PKG)
root = ET.parse(B/"window_dump.xml").getroot()

def bds(s):
    m = list(map(int, re.findall(r"\d+", s or "")))
    return (m[0], m[1], m[2], m[3]) if len(m) >= 4 else None

c = []
for el in root.iter("node"):
    if PKG not in (el.attrib.get("package") or PKG): continue
    desc = (el.attrib.get("content-desc") or "").strip()
    txt = (el.attrib.get("text") or "").strip()
    b = bds(el.attrib.get("bounds", ""))
    if not b: continue
    cx, cy = (b[0]+b[2])//2, (b[1]+b[3])//2
    if cy < 280: continue
    if desc == "Copy message" and el.attrib.get("clickable") == "true":
        c.append((b[3]+3000, cx, cy, "Copy message"))
    if txt == "Copy" and el.attrib.get("clickable") == "true" and 400 < cy < 1900:
        c.append((b[3]+2000, cx, cy, "Copy"))
if not c:
    print(json.dumps({"ok": False, "error": "no Copy visible"})); sys.exit(1)
c.sort(reverse=True)
_, x, y, lab = c[0]
print(json.dumps({"ok": True, "x": x, "y": y, "label": lab}))
