#!/usr/bin/env python3
import hashlib, json, re, sys
from pathlib import Path
XML = Path.home() / "broccoli/ui/last_ui.xml"
SKIP = re.compile(r"^(Ask|Send|Grok|Start new chat|Imagine|Explore|Menu|Search|Imagine|Explore|Menu|Search|\s*)$", re.I)

def load():
    if not XML.is_file() or XML.stat().st_size < 400:
        return ""
    t = XML.read_text(encoding="utf-8", errors="replace")
    return t if "ai.x.grok" in t else ""

def lines(xml):
    out, seen = [], set()
    for m in re.finditer(r'text="([^"]{1,6000})"', xml):
        t = m.group(1).strip()
        if SKIP.match(t) or t.startswith("BROCCOLI_") or "Findings (priority" in t:
            continue
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out

def last(user=""):
    xml = load()
    if not xml:
        return {"ok": False, "last": ""}
    L = lines(xml)
    u = (user or "").strip()
    while L and u and (L[-1] == u or (len(u) > 8 and u[:30] in L[-1] and len(L[-1]) <= len(u) + 30)):
        L.pop()
    if L and u and L[-1] == u:
        L.pop()
    tail = L[-1] if L else ""
    fp = hashlib.md5("\n".join(L[-25:]).encode()).hexdigest()
    return {"ok": True, "last": tail, "fp": fp, "tail": L[-8:]}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "last"
    msg = sys.argv[2] if len(sys.argv) > 2 else ""
    r = last(msg)
    if cmd == "json":
        print(json.dumps(r, ensure_ascii=False))
    elif cmd == "fp":
        print(r.get("fp", ""))
    elif cmd == "last":
        print(r.get("last", ""))
    elif cmd == "lines":
        for x in r.get("tail", []):
            print(x)
