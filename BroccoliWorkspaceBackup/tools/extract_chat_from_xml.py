#!/usr/bin/env python3
import re, sys
from pathlib import Path
p = Path("/data/local/tmp/broccoli_ui.xml")
if not p.is_file():
    p = Path.home() / "broccoli/ui/last_ui.xml"
xml = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else ""
skip = re.compile(r'^(Ask|Send|Grok|Imagine|Explore|Home|Settings|\s*)$', re.I)
for m in re.finditer(r'text="([^"]{2,500})"', xml):
    t = m.group(1).strip()
    if not t or skip.match(t) or t.startswith("Reply with only"):
        continue
    if "PONG" in t or len(t) > 8:
        print(t)
