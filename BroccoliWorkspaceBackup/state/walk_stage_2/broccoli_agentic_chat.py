import os, time, json, subprocess
from pathlib import Path
from broccoli_rish_shell import shell
from broccoli_ui_dump import ui_dump, nodes, find_send, last_reply_text, find_grok_search_box
from broccoli_input import inject_prompt, wait_for_search_box

BRO = Path.home() / "broccoli"
STATE = BRO / "state"
LOG = BRO / "reports/agentic.log"
GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")

def log(msg):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    prev = LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else ""
    LOG.write_text(prev + time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n", encoding="utf-8")

def stopped(): return (STATE/"STOP").exists()

def open_grok():
    shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
    time.sleep(0.35)
    shell(f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {GROK} 2>/dev/null")
    time.sleep(0.4)

def read_task_prompt():
    for path in (BRO/"inbox/prompt.txt", BRO/"meta/task_queue.txt"):
        if path.exists():
            raw = path.read_text(encoding="utf-8", errors="replace").strip()
            if not raw: continue
            for line in raw.splitlines():
                line = line.strip()
                if not line: continue
                if "|" in line and ("ASK" in line.upper() or "TASK" in line.upper()):
                    return line.split("|", 1)[-1].strip()
                if line.upper().startswith("ASK|"):
                    return line[4:].strip()
                return line
    return "BROCC_TASK reply LOOP_OK"

def codev_round(prompt):
    from broccoli_input import clip_set
    clip_set(prompt)
    (BRO/"inbox/prompt.txt").write_text(prompt, encoding="utf-8")
    sp = subprocess.run(["brocc", "agent", "codev", "start"], cwd=str(BRO), timeout=120, capture_output=True, text=True)
    log(f"CODEV rc={sp.returncode}")
    pull = Path("/sdcard/Broccoli/pull")
    if pull.exists():
        bs = sorted(pull.glob("bundle_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if bs:
            txt = bs[0].read_text(encoding="utf-8", errors="replace")
            (BRO/"inbox/grok_reply.txt").write_text(txt, encoding="utf-8")
            return {"ok": True, "via": "codev", "reply": txt}
    return {"ok": False, "error": "codev_no_pull"}

def send_prompt_agentic(prompt=None):
    if stopped(): return {"ok": False, "error": "USER_STOP"}
    prompt = (prompt or read_task_prompt()).strip()
    log(f"ROUND task_len={len(prompt)}")
    open_grok()
    box, xml0, dt_box = wait_for_search_box(GROK, max_s=5.0)
    log(f"SEARCH_BOX found={bool(box)} wait_dt={dt_box:.2f}")
    ok_in, xml_send, _ = inject_prompt(prompt, GROK)
    log(f"INJECT ok={ok_in}")
    if not ok_in:
        return codev_round(prompt)

    ns = nodes(xml_send)
    snd = find_send(ns, GROK)
    if snd:
        shell(f"input tap {snd['cx']} {snd['cy']}")
    else:
        shell("input keyevent 66")
    time.sleep(0.18)
    log("SENT")

    before = last_reply_text(ns, GROK)
    t0 = time.time()
    max_wait = float(os.environ.get("BROCCOLI_RECV_MAX", "20"))
    last = ""
    while time.time() - t0 < max_wait:
        if stopped(): return {"ok": False, "error": "USER_STOP"}
        shell("input swipe 540 1500 540 800 220")
        time.sleep(0.12)
        ta = last_reply_text(nodes(ui_dump()), GROK)
        if ta and ta != before and len(ta) >= 3:
            (BRO/"inbox/grok_reply.txt").write_text(ta, encoding="utf-8")
            log(f"RECV ok len={len(ta)}")
            return {"ok": True, "reply": ta, "via": "ui"}
        if len(ta) > len(last): last = ta
        time.sleep(0.1)
    if last:
        (BRO/"inbox/grok_reply.txt").write_text(last, encoding="utf-8")
        return {"ok": True, "partial": True, "reply": last, "via": "ui"}
    return codev_round(prompt)
