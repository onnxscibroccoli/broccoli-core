#!/usr/bin/env python3
import json, re, sys
from pathlib import Path
HOME = Path.home()
XML = HOME / "broccoli/ui/last_ui.xml"
GROK = "ai.x.grok"
NOISE = re.compile(r"^(Ask|Send|Grok|Imagine|Explore|Home|Menu|Search|Voice|New chat|\s*)$", re.I)

def load():
    for p in [XML, Path("/data/local/tmp/broccoli_ui.xml")]:
        if p.is_file() and p.stat().st_size > 500:
            t = p.read_text(encoding="utf-8", errors="replace")
            if "<hierarchy" in t:
                return t
    return ""

def nodes(xml):
    out = []
    for m in re.finditer(r"<node([^>]+)/?>", xml):
        a = m.group(1)
        def g(k):
            mm = re.search(rf'{k}="([^"]*)"', a)
            return mm.group(1) if mm else ""
        out.append({"text": g("text"), "desc": g("content-desc"), "rid": g("resource-id"),
                    "klass": g("class"), "pkg": g("package"), "bounds": g("bounds")})
    return out

def chat_lines(xml):
    lines, seen = [], set()
    for n in nodes(xml):
        for f in ("text", "desc"):
            t = (n[f] or "").strip()
            if len(t) < 2 or len(t) > 6000 or NOISE.match(t):
                continue
            if t in seen:
                continue
            seen.add(t)
            lines.append(t)
    return lines

def report():
    xml = load()
    if not xml:
        return {"ok": False, "reason": "no_xml"}
    lines = chat_lines(xml)
    comp = any("chat_text_input" in n["rid"] or ("EditText" in n["klass"] and GROK in n["pkg"]) for n in nodes(xml))
    return {"ok": True, "grok_fg": GROK in xml, "has_composer": comp,
            "chat_lines": lines[-20:], "last": lines[-1] if lines else "", "bytes": len(xml)}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    r = report()
    if cmd == "report":
        print(json.dumps(r, indent=2, ensure_ascii=False))
    elif cmd == "lines":
        for ln in r.get("chat_lines", []):
            print(ln)
    elif cmd == "last":
        print(r.get("last", ""))
