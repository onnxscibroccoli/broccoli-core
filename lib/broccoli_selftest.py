import json, time
from pathlib import Path
from broccoli_rish_shell import rish_ok, shell
from broccoli_ui_dump import ui_dump, nodes, dump_debug_summary
from broccoli_input import clip_set, clip_get

BRO = Path.home() / "broccoli"

def run_selftest(open_grok_fn=None):
    rep = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "steps": []}
    ok_r, rish = rish_ok()
    rep["steps"].append({"rish": ok_r, "info": rish[:200]})
    clip_set("SELFTEST_CLIP")
    rep["steps"].append({"clipboard": "SELFTEST_CLIP" in clip_get()})
    if open_grok_fn:
        open_grok_fn()
        time.sleep(0.35)
    xml = ui_dump()
    ns = nodes(xml)
    rep["dump_bytes"] = len(xml)
    rep["ui"] = dump_debug_summary(ns)
    rep["ok"] = ok_r and len(xml) > 200 and rep["ui"].get("sends")
    out = BRO / "reports/selftest_last.json"
    out.write_text(json.dumps(rep, indent=2), encoding="utf-8")
    return rep
