#!/usr/bin/env python3
"""Self-test: rish, dump, composer visible, optional dry send marker."""
import json, sys
from pathlib import Path
BRO = Path.home() / "broccoli"
sys.path.insert(0, str(BRO / "lib"))

def main():
    from broccoli_rish_shell import rish_ok, shell, rish_path
    from broccoli_ui_dump import ui_dump, nodes, find_composer, find_send
    from broccoli_agentic_chat import open_grok_chat, GROK_PKG

    rep = {"rish_path": rish_path(), "steps": []}
    ok, info = rish_ok()
    rep["steps"].append({"rish": ok, "info": info[:300]})
    open_grok_chat()
    xml = ui_dump()
    rep["dump_bytes"] = len(xml)
    ns = nodes(xml)
    comp = find_composer(ns, GROK_PKG)
    snd = find_send(ns, GROK_PKG)
    rep["steps"].append({
        "nodes": len(ns),
        "composer": bool(comp),
        "send": bool(snd),
        "pkg": GROK_PKG,
    })
    rep["ok"] = ok and len(xml) > 500 and comp is not None
    out = BRO / "reports/agentic_selftest.json"
    out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    print(json.dumps(rep, indent=2))
    print("SELFTEST_OK" if rep["ok"] else "SELFTEST_FAIL")
    sys.exit(0 if rep["ok"] else 1)

if __name__ == "__main__":
    main()
