import os, re, time, json, xml.etree.ElementTree as ET
from pathlib import Path
from broccoli_rish_shell import shell, wm_size
from broccoli_notif import recv_via_notifications, status_notify, log_round as notif_log
from broccoli_xml_sanitize import sanitize_xml, parse_nodes_regex

GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
BRO = Path.home() / "broccoli"
NO_ENTER = os.environ.get("BROCCOLI_NO_ENTER", "1") == "1"
SEND_MODE = os.environ.get("BROCCOLI_SEND_MODE", "sibling_first")
LOG = BRO / "reports/infinite.log"

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as _lf:
        _lf.write(time.strftime("%H:%M:%S ")+m+"\n")

def dump_xml():
    remote = "/data/local/tmp/broccoli_ui.xml"
    for c in (
        f"uiautomator dump {remote} 2>/dev/null; cat {remote}",
        f"cmd uiautomator dump {remote} 2>/dev/null; cat {remote}",
    ):
        _, out = shell(c, timeout=22)
        clean = sanitize_xml(out)
        if len(clean) > 200:
            (BRO/"ui/last_dump.xml").write_text(clean[:3_000_000], encoding="utf-8")
            return clean
    return ""

def parse_tree(xml):
    xml = sanitize_xml(xml)
    parent, nodes = {}, []
    if not xml:
        return None, parent, []
    try:
        root = ET.fromstring(xml.encode("utf-8", errors="replace"))
        parent = {c: p for p in root.iter() for c in p}
        for el in root.iter("node"):
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", el.get("bounds") or "")
            if not m: continue
            x1,y1,x2,y2 = map(int, m.groups())
            nodes.append({
                "el": el,
                "text": (el.get("text") or "").strip(),
                "desc": (el.get("content-desc") or "").strip(),
                "rid": el.get("resource-id") or "",
                "cls": el.get("class") or "",
                "pkg": el.get("package") or "",
                "clickable": el.get("clickable") == "true",
                "enabled": el.get("enabled") != "false",
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "cx": (x1+x2)//2, "cy": (y1+y2)//2,
            })
    except ET.ParseError as e:
        log(f"xml_et_fail {e}")
        nodes = parse_nodes_regex(xml, GROK) or parse_nodes_regex(xml, None)
        for n in nodes:
            n["el"] = None
    return None, parent, nodes

def in_grok(n):
    return GROK in (n.get("pkg") or "")

def tap(cx, cy, label=""):
    shell(f"input tap {int(cx)} {int(cy)}")
    time.sleep(0.35)
    return {"method": "adb_tap", "cx": int(cx), "cy": int(cy), "label": label}

def manual_send_coords():
    for p in (BRO/"meta/manual_send_tap.txt", BRO/"meta/send_xy.txt"):
        if p.exists():
            try:
                a, b = p.read_text().strip().split()[:2]
                return int(a), int(b), "manual_file"
            except ValueError:
                pass
    return None

def score_send(n, comp):
    if not n.get("clickable") or n.get("enabled") is False:
        return -1
    blob = (n.get("text","")+" "+n.get("desc","")+" "+n.get("rid","")).lower()
    s = 0
    if "send" in blob: s += 300
    if "send" in (n.get("rid") or "").lower(): s += 200
    if comp:
        if abs(n["cy"]-comp["cy"]) > 110: s -= 60
        if n["cx"] <= comp.get("x2", 0) - 8: s -= 120
        else: s += (n["cx"] - comp.get("x2", 0)) // 2
    return s

def find_composer(nodes):
    pool = [n for n in nodes if in_grok(n)] or nodes
    best, sc = None, -1
    for n in pool:
        b = (n["text"]+" "+n["desc"]+" "+n["rid"]).lower()
        s = ("edittext" in (n.get("cls") or "").lower()) * 100
        if any(k in b for k in ("ask","search","message","compose")): s += 25
        s += n["cy"] // 20
        if s > sc: sc, best = s, n
    return best

def find_send(nodes, parent_map, comp_el, comp):
    cands = []
    # 1) siblings of composer
    if comp_el and parent_map:
        par = parent_map.get(comp_el)
        if par is not None:
            for el in par:
                if el.tag != "node" or el is comp_el: continue
                m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", el.get("bounds") or "")
                if not m: continue
                x1,y1,x2,y2 = map(int, m.groups())
                sn = {"clickable": el.get("clickable")=="true", "enabled": el.get("enabled")!="false",
                      "text": (el.get("text") or "").strip(), "desc": (el.get("content-desc") or "").strip(),
                      "rid": el.get("resource-id") or "", "cls": el.get("class") or "",
                      "x1":x1,"y1":y1,"x2":x2,"y2":y2,"cx":(x1+x2)//2,"cy":(y1+y2)//2}
                sc = score_send(sn, comp)
                if sc > 5:
                    cands.append((sc+500, sn, "sibling"))
    # 2) semantic in grok row
    if SEND_MODE != "sibling_only":
        for n in nodes:
            if not in_grok(n): continue
            sc = score_send(n, comp)
            if sc > 40:
                cands.append((sc, n, "semantic"))
    if cands:
        cands.sort(key=lambda x: -x[0])
        b = cands[0][1]
        return {**b, "strategy": cands[0][2], "score": cands[0][0]}
    # 3) same row rightmost clickable (still NO enter)
    if comp and SEND_MODE != "sibling_only":
        row = []
        for n in nodes:
            if not in_grok(n) or not n.get("clickable"): continue
            if abs(n["cy"]-comp["cy"]) > 100: continue
            if n["cx"] > comp.get("x2", 0) - 5:
                row.append(n)
        if row:
            n = max(row, key=lambda x: x["cx"])
            return {**n, "strategy": "row_right", "score": n["cx"]}
    # 4) manual calibrated
    mc = manual_send_coords()
    if mc:
        return {"cx": mc[0], "cy": mc[1], "strategy": mc[2], "rid": "", "desc": ""}
    # 5) geometry fallback
    if comp:
        w, _ = wm_size()
        return {"cx": min(w-40, comp["x2"]+95), "cy": comp["cy"], "strategy": "geom_right", "rid": "", "desc": ""}
    return None

def normalize_task(task):
    task = (task or "").strip()
    lines = [ln.strip() for ln in task.splitlines() if ln.strip()]
    for pref in ("BROCC_TASK", "BROCC_WALK"):
        for ln in lines:
            if ln.startswith(pref):
                return ln
    return lines[-1] if lines else task

def composer_has_text(nodes, comp, needle):
    if not comp: return False
    parts = []
    for n in nodes:
        if not in_grok(n): continue
        if n.get("text") and abs(n["cy"]-comp["cy"]) < 160:
            parts.append(n["text"])
    blob = " ".join(parts)
    n = normalize_task(needle)
    return n in blob or n[:16] in blob or "BROCC_TASK" in blob and "BROCC_TASK" in blob

def last_assistant(nodes):
    skip = ("ask anything","search","send","menu","settings","attach","voice")
    msgs = []
    for n in nodes:
        if not in_grok(n): continue
        t = n.get("text") or ""
        if len(t) < 4 or "edittext" in (n.get("cls") or "").lower(): continue
        if any(s in t.lower() for s in skip) and len(t) < 50: continue
        msgs.append((n["cy"], t))
    msgs.sort()
    return msgs[-1][1] if msgs else ""

def adb_click_send(comp, xml=None):
    xml = xml or dump_xml()
    if len(xml) < 80:
        return False, {"error": "empty_dump"}
    _, parent, nodes = parse_tree(xml)
    comp_n = find_composer(nodes)
    comp_el = comp_n.get("el") if comp_n else None
    comp_d = comp_n or comp
    send = find_send(nodes, parent, comp_el, comp_d)
    if not send:
        log("send_adb FAIL no_target")
        return False, {"error": "no_send"}
    r = tap(send["cx"], send["cy"], send.get("strategy", "adb"))
    r["rid"] = send.get("rid", "")
    r["strategy"] = send.get("strategy")
    (BRO/"meta/last_send_adb.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    (BRO/"meta/manual_send_tap.txt").write_text(f"{send['cx']} {send['cy']}\n", encoding="utf-8")
    log(f"send_adb {send['cx']} {send['cy']} {send.get('strategy')}")
    return True, r

def inject_paste(task):
    task = normalize_task(task)
    shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
    time.sleep(0.5)
    xml = dump_xml()
    _, _, nodes = parse_tree(xml)
    comp = find_composer(nodes)
    w, h = wm_size()
    if not comp:
        comp = {"cx": w//2, "cy": int(h*0.88), "x2": w//2}
    if not composer_has_text(nodes, comp, task):
        shell(f"input tap {comp['cx']} {comp['cy']}")
        time.sleep(0.15)
        shell("input keyevent 122")
        shell("input keyevent 279")
        time.sleep(0.3)
        log("inject paste279")
    else:
        log("inject skip_visible")
    return comp

import os
# BROCCOLI_REQUIRE_SEND=1 → abort round if send fails

def full_round_adb(task, clip_set_fn):
    task = normalize_task(task)
    if not task:
        return {"ok": False, "error": "empty"}
    if not clip_set_fn(task):
        return {"ok": False, "stage": "clipboard"}
    comp = inject_paste(task)
    xml1 = dump_xml()
    _, _, nodes1 = parse_tree(xml1)
    comp = find_composer(nodes1) or comp
    if not composer_has_text(nodes1, comp, task):
        return {"ok": False, "stage": "inject_verify"}
    before = last_assistant(nodes1)
    sent, smeta = adb_click_send(comp, xml1)
    if not sent:
        return {"ok": False, "stage": "send", "detail": smeta}
    time.sleep(0.45)
    for attempt in range(3):
        xml2 = dump_xml()
        _, _, nodes2 = parse_tree(xml2)
        comp2 = find_composer(nodes2) or comp
        if not composer_has_text(nodes2, comp2, task):
            log("send_verify composer_cleared
    from broccoli_recv_copy_rish import recv_via_copy_rish
    reply, rmeta = recv_via_copy_rish(task=task)
    log(f"recv path=copy_rish meta={rmeta}")
    if not reply:
        return {"ok": False, "stage": "recv_failed", "reply": "", "reply_head": ""}")
            break
        log(f"send_retry tap attempt={attempt+1}")
        adb_click_send(comp2, xml2)
        time.sleep(0.4)
    t0 = time.time()
    reply = ""
    while time.time() - t0 < float(os.environ.get("BROCCOLI_RECV_MAX", "35")):
        shell("input swipe 540 1500 540 800 220")
        time.sleep(0.12)
        ta = last_assistant(parse_tree(dump_xml())[2])
        if ta and ta != before and len(ta) >= 3:
            reply = ta
            break
        time.sleep(0.1)
    if not reply:
        notif_log("recv_try_notif", f"before_len={len(before)}")
        nreply, nmeta = recv_via_notifications(before=before, max_wait=float(os.environ.get("BROCCOLI_NOTIF_RECV_MAX", "18")))
        if nreply:
            reply = nreply
            log(f"recv_notif ok head={(reply or '')[:60]}")
    if reply:
        (BRO/"inbox/grok_reply.txt").write_text(reply, encoding="utf-8")
    try:
        status_notify("Broccoli", f"{'OK' if reply else 'wait'}: {(reply or 'no reply')[:80]}")
    except Exception:
        pass
    ok = bool(reply) and ("LOOP_OK" in reply or len(reply) > 6)
    log(f"round ok={ok} loop_ok={'LOOP_OK' in (reply or '')} head={(reply or '')[:80]}")
    return {"ok": ok, "send": smeta, "no_enter": NO_ENTER, "loop_ok": "LOOP_OK" in (reply or ""),
            "reply_head": (reply or "")[:320]}


def composer_cleared_or_sent():
    xml = dump_ui_xml()
    if not xml:
        return False
    low = xml.lower()
    if "brocc_task" in low and "edittext" in low:
        return False
    return True
