import os, time, json, subprocess
from pathlib import Path
from broccoli_rish_shell import shell
from broccoli_ui_dump import ui_dump, nodes, last_reply_text, dump_debug_summary
from broccoli_input import inject_prompt, wait_for_search_box, clip_set
from broccoli_send import auto_send
from broccoli_selftest import run_selftest
from broccoli_strategy import log_path

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
    time.sleep(0.3)
    shell(f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {GROK} 2>/dev/null")
    time.sleep(0.35)

def read_task_prompt():
    p = BRO/"inbox/prompt.txt"
    if p.exists() and p.stat().st_size:
        return p.read_text(encoding="utf-8").strip()
    q = BRO/"meta/task_queue.txt"
    if q.exists():
        for line in reversed(q.read_text(encoding="utf-8", errors="replace").splitlines()):
            line = line.strip()
            if "|" in line and "ASK" in line.upper():
                return line.split("|",1)[-1].strip()
    return "BROCC_TASK reply exactly: LOOP_OK"

def codev_round(prompt):
    clip_set(prompt)
    (BRO/"inbox/prompt.txt").write_text(prompt, encoding="utf-8")
    sp = subprocess.run(["brocc","agent","codev","start"], cwd=str(BRO), timeout=120, capture_output=True, text=True)
    log(f"CODEV rc={sp.returncode}")
    pull = Path("/sdcard/Broccoli/pull")
    if pull.exists():
        bs = sorted(pull.glob("bundle_*"), key=lambda p: p.stat().st_mtime, reverse=True)
        if bs:
            txt = bs[0].read_text(encoding="utf-8", errors="replace")
            (BRO/"inbox/grok_reply.txt").write_text(txt, encoding="utf-8")
            log_path("recv", "codev_pull", True)
            return {"ok": True, "via": "codev", "reply": txt}
    return {"ok": False, "error": "codev_no_pull"}

def send_prompt_agentic(prompt=None):
    if stopped(): return {"ok": False, "error": "USER_STOP"}
    prompt = (prompt or read_task_prompt()).strip()
    max_rounds = int(os.environ.get("BROCCOLI_PERSIST_ROUNDS", "3"))

    for attempt in range(1, max_rounds + 1):
        log(f"ROUND attempt={attempt} len={len(prompt)}")
        open_grok()
        box, _, dt = wait_for_search_box(GROK, max_s=4.0)
        log(f"SEARCH_BOX found={bool(box)} dt={dt:.2f}")

        ok_in, xml_in, _ = inject_prompt(prompt, GROK)
        log(f"INJECT ok={ok_in}")
        if not ok_in:
            if attempt >= 2:
                st = run_selftest(open_grok)
                log(f"SELFTEST {json.dumps(st.get('ui',{}))[:400]}")
            continue

        sent_ok = False
        send_method = None
        retries = int(os.environ.get("BROCCOLI_SEND_RETRIES", "4"))
        for sr in range(retries):
            sent_ok, send_method, xml_sent = auto_send(GROK, xml_in)
            log(f"SEND try={sr} ok={sent_ok} method={send_method}")
            if sent_ok:
                break
            time.sleep(0.15)
            xml_in = ui_dump()

        if not sent_ok:
            if attempt >= 2:
                st = run_selftest(open_grok)
                (BRO/"reports/send_fail_dump.json").write_text(json.dumps(st, indent=2), encoding="utf-8")
            continue

        before = last_reply_text(nodes(xml_sent), GROK)
        t0 = time.time()
        max_wait = float(os.environ.get("BROCCOLI_RECV_MAX", "22"))
        last = ""
        while time.time() - t0 < max_wait:
            if stopped(): return {"ok": False, "error": "USER_STOP"}
            shell("input swipe 540 1500 540 800 200")
            time.sleep(0.1)
            ta = last_reply_text(nodes(ui_dump()), GROK)
            if ta and ta != before and len(ta) >= 3:
                (BRO/"inbox/grok_reply.txt").write_text(ta, encoding="utf-8")
                log(f"RECV ok method={send_method} len={len(ta)}")
                log_path("recv", "ui_poll", True, {"send_method": send_method})
                return {"ok": True, "reply": ta, "via": "ui", "send_method": send_method}
            if len(ta) > len(last): last = ta
            time.sleep(0.08)

        if last:
            (BRO/"inbox/grok_reply.txt").write_text(last, encoding="utf-8")
            log_path("recv", "ui_partial", True)
            return {"ok": True, "partial": True, "reply": last, "via": "ui"}

        log("RECV timeout retry")
        if attempt >= 2:
            run_selftest(open_grok)

    log("PERSIST exhausted -> codev")
    return codev_round(prompt)
