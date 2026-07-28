#!/usr/bin/env python3
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

B = Path(os.environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
PKG = "ai.x.grok"

if (B / "chat_profile.json").is_file():
    try:
        prof = json.loads((B / "chat_profile.json").read_text(encoding="utf-8"))
        PKG = prof.get("chat_package", PKG)
    except Exception:
        pass

window_dump_path = B / "window_dump.xml"
if not window_dump_path.is_file():
    print(json.dumps({"ok": False, "error": "window_dump.xml missing"}))
    sys.exit(1)

try:
    root = ET.parse(window_dump_path).getroot()
except Exception as e:
    print(json.dumps({"ok": False, "error": f"XML parse failure: {str(e)}"}))
    sys.exit(1)

def bds(s):
    m = list(map(int, re.findall(r"\d+", s or "")))
    return (m[0], m[1], m[2], m[3]) if len(m) >= 4 else None

c = []
for el in root.iter("node"):
    if PKG not in (el.attrib.get("package") or PKG):
        continue
    desc = (el.attrib.get("content-desc") or "").strip()
    txt = (el.attrib.get("text") or "").strip()
    b = bds(el.attrib.get("bounds", ""))
    if not b:
        continue
    
    cx, cy = (b[0] + b[2]) // 2, (b[1] + b[3]) // 2
    if cy < 280:
        continue
        
    if desc == "Copy message" and el.attrib.get("clickable") == "true":
        c.append((b[3] + 3000, cx, cy, "Copy message"))
    if txt == "Copy" and el.attrib.get("clickable") == "true" and 400 < cy < 1900:
        c.append((b[3] + 2000, cx, cy, "Copy"))

if not c:
    print(json.dumps({"ok": False, "error": "No 'Copy' interactive elements visible"}))
    sys.exit(1)

c.sort(reverse=True)
_, x, y, lab = c[0]
print(json.dumps({"ok": True, "x": x, "y": y, "label": lab}))
