"""Send Grok message: A11y helper -> Enter on focused field -> dump node click."""
import os, time
from broccoli_rish_shell import shell
from broccoli_ui_dump import ui_dump, nodes, find_grok_search_box, last_reply_text
from broccoli_a11y_rish import (
    a11y_installed, a11y_service_enabled, a11y_click_send,
    a11y_set_text, a11y_click_text, a11y_status, open_accessibility_settings,
)
from broccoli_strategy import log_path

GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")

def task_still_visible(ns, task):
    box = find_grok_search_box(ns, GROK)
    if not box:
        return False
    blob = []
    for n in ns:
        if GROK not in (n.get("pkg") or ""): continue
        if n.get("text") and abs(n.get("cy",0) - box["cy"]) < 140:
            blob.append(n["text"])
    s = " ".join(blob)
    return task[:16] in s or "BROCC_TASK" in s

def send_via_a11y(task, pkg=None):
    pkg = pkg or GROK
    st = a11y_status()
    log_path("send", "a11y_status", st["enabled"], st)

    if st["installed"] and st["enabled"]:
        a11y_set_text(task, pkg)
        time.sleep(0.2)
        ok, out = a11y_click_send(pkg)
        log_path("send", "a11y_click_send", ok, {"out": (out or "")[:120]})
        if ok:
            return True, "a11y_click_send"

    # focused EditText + Enter (no coords)
    shell("input keyevent 66")
    time.sleep(0.3)
    ns = nodes(ui_dump())
    if not task_still_visible(ns, task):
        log_path("send", "keyevent_66", True)
        return True, "keyevent_66"

    # a11y text click attempts without APK (broadcast no-op if missing)
    for label in ("Send", "submit", "Go"):
        a11y_click_text(label, pkg)
        ns = nodes(ui_dump())
        if not task_still_visible(ns, task):
            log_path("send", f"a11y_text_{label}", True)
            return True, f"a11y_text_{label}"

    return False, "send_failed"

def full_round_a11y(task):
    from broccoli_agentic_chat import open_grok
    from broccoli_input import clip_set, wait_for_search_box, task_already_in_composer
    from pathlib import Path
    BRO = Path.home() / "broccoli"

    open_grok()
    clip_set(task)
    box, xml, _ = wait_for_search_box(GROK, 4.0)
    if box and not task_already_in_composer(nodes(xml), box, task):
        shell(f"input tap {int(box['cx'])} {int(box['cy'])}")
        time.sleep(0.1)
        shell("input keyevent 122")
        shell("input keyevent 279")

    before = last_reply_text(nodes(ui_dump()), GROK)
    sent, method = send_via_a11y(task, GROK)

    t0 = time.time()
    last = ""
    while time.time() - t0 < float(os.environ.get("BROCCOLI_RECV_MAX", "28")):
        shell("input swipe 540 1500 540 800 200")
        time.sleep(0.1)
        ta = last_reply_text(nodes(ui_dump()), GROK)
        if ta and ta != before and len(ta) >= 3:
            (BRO / "inbox/grok_reply.txt").write_text(ta, encoding="utf-8")
            return {"ok": True, "via": "a11y", "send_method": method, "reply": ta}
        if len(ta) > len(last): last = ta
        time.sleep(0.08)
    return {"ok": sent, "partial": bool(last), "send_method": method, "reply": last}
