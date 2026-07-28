"""Manual-send mode: clip + focus only; user taps send."""
import os, time, json
from pathlib import Path
from broccoli_rish_shell import shell
from broccoli_ui_dump import ui_dump, nodes, dump_debug_summary, find_grok_search_box
from broccoli_input import clip_set, wait_for_search_box

BRO = Path.home() / "broccoli"
GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")

def prepare_only(prompt):
    prompt = (prompt or "").strip()
    if prompt:
        clip_set(prompt)
        Path(BRO/"inbox/prompt.txt").write_text(prompt, encoding="utf-8")
    shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
    time.sleep(0.35)
    box, xml, dt = wait_for_search_box(GROK, max_s=4.0)
    if box and prompt:
        shell(f"input tap {int(box['cx'])} {int(box['cy'])}")
        time.sleep(0.08)
        shell("input keyevent 122")
        shell("input keyevent 279")
    xml = ui_dump()
    ns = nodes(xml)
    summary = dump_debug_summary(ns, GROK)
    out = BRO / "reports/ui_send_targets.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
