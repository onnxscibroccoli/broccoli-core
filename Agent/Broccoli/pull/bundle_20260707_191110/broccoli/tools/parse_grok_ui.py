#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
p = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "broccoli/reports/ui_dump.xml")
x = p.read_text(errors="replace") if p.is_file() else ""
o = {"bytes": len(x), "package": None, "composer": None, "send": None, "ok": False}
if "NO_RISH" in x:
    print(json.dumps(o)); raise SystemExit(0)
m = re.search(r'package="([^"]+)"', x)
if m: o["package"] = m.group(1)
best = None
for m in re.finditer(r'class="android\.widget\.EditText"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x):
    y1 = int(m.group(2))
    if best is None or y1 > best[0]: best = (y1, m)
if best:
    g = best[1]
    o["composer"] = {"x": (int(g[0])+int(g[2]))//2, "y": (int(g[1])+int(g[3]))//2}
m = re.search(r'text="Send"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', x, re.I)
if m:
    o["send"] = {"x": (int(m.group(1))+int(m.group(3)))//2, "y": (int(m.group(2))+int(m.group(4)))//2}
o["ok"] = bool(o.get("package") and "grok" in o["package"].lower() and o["bytes"] >= 5000 and o["composer"])
print(json.dumps(o))
