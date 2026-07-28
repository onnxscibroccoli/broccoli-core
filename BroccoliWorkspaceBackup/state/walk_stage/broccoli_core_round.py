"""One full round: clip -> inject (no clear) -> send -> recv. Rish only."""
import os, re, time, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from broccoli_rish_shell import shell, wm_size

GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
BRO = Path.home() / "broccoli"
PREFIX = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")
LOG = BRO / "reports/infinite.log"

def log(m):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text((LOG.read_text(encoding="utf-8", errors="replace") if LOG.exists() else "") +
                   time.strftime("%H:%M:%S ") + m + "\n", encoding="utf-8")

def clip_set(text):
    cs = Path(PREFIX) / "bin/termux-clipboard-set"
    if not cs.is_file(): return False
    subprocess.run([str(cs), text], timeout=8, check=False)
    time.sleep(0.05)
    return True

def dump_xml():
    r = "/data/local/tmp/broccoli_ui.xml"
    for c in (f"uiautomator dump --compressed {r} 2>/dev/null; cat {r}",
              f"cmd uiautomator dump {r} 2>/dev/null; cat {r}"):
        _, out = shell(c, timeout=18)
        if "<?xml" in out:
            x = out[out.find("<?xml"):]
            (BRO/"ui/last_dump.xml").write_text(x[:2_000_000], encoding="utf-8")
            return x
    return ""

def parse(xml):
    if not xml: return []
    try:
        root = ET.fromstring(xml.encode("utf-8", errors="replace"))
    except ET.ParseError:
        return []
    out = []
    for el in root.iter("node"):
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", el.get("bounds") or "")
        if not m: continue
        x1,y1,x2,y2 = map(int, m.groups())
        out.append({
            "text": (el.get("text") or "").strip(),
            "desc": (el.get("content-desc") or "").strip(),
            "rid": el.get("resource-id") or "",
            "cls": el.get("class") or "",
            "pkg": el.get("package") or "",
            "clickable": el.get("clickable") == "true",
            "cx": (x1+x2)//2, "cy": (y1+y2)//2,
            "x1": x1, "x2": x2, "y1": y1, "y2": y2,
        })
    return out

def grok(ns): return [n for n in ns if GROK in (n.get("pkg") or "")] or ns

def composer(ns):
    pool = grok(ns)
    best, sc = None, -1
    for n in pool:
        b = (n["text"]+" "+n["desc"]+" "+n["rid"]).lower()
        s = ("edittext" in n["cls"].lower())*70
        if any(k in b for k in ("ask","search","message","compose")): s += 20
        s += n["cy"]//35
        if s > sc: sc, best = s, n
    return best

def composer_blob(ns, comp):
    if not comp: return ""
    parts = []
    for n in grok(ns):
        if n.get("text") and abs(n["cy"]-comp["cy"]) < 130:
            parts.append(n["text"])
    return " ".join(parts)

def task_visible(ns, comp, task):
    blob = composer_blob(ns, comp)
    head = task.strip()[:24]
    return head in blob or task.strip()[:12] in blob

def send_node(ns, comp):
    wp = BRO / "meta/manual_send_tap.txt"
    if wp.exists():
        try:
            a, b = wp.read_text().split()[:2]
            return {"cx": int(a), "cy": int(b), "src": "manual_send_tap"}
        except ValueError:
            pass
    wp2 = BRO / "meta/working_paths.json"
    if wp2.exists():
        try:
            d = json.loads(wp2.read_text())
            for e in d.get("send", []):
                if e.get("ok") and "cx" in e:
                    return {"cx": int(e["cx"]), "cy": int(e["cy"]), "src": "working_paths"}
        except Exception:
            pass
    if not comp: return None
    row = []
    for n in grok(ns):
        if not n["clickable"]: continue
        if abs(n["cy"]-comp["cy"]) > 110: continue
        if n["cx"] <= comp["x2"]-12: continue
        blob = (n["text"]+" "+n["desc"]+" "+n["rid"]).lower()
        sc = n["cx"] + ("send" in blob)*5000
        row.append((sc, n))
    if row:
        row.sort(key=lambda x: -x[0])
        n = row[0][1]
        return {"cx": n["cx"], "cy": n["cy"], "src": "dump_row"}
    w, _ = wm_size()
    far = [n for n in grok(ns) if n["clickable"] and n["cx"] > w*0.82 and n["cy"] > comp["cy"]-80]
    if far:
        n = max(far, key=lambda x: x["cx"])
        return {"cx": n["cx"], "cy": n["cy"], "src": "far_right"}
    return None

def last_reply(ns):
    skip = ("ask anything","search","send","menu","settings","attach","voice")
    msgs = []
    for n in grok(ns):
        t = n.get("text") or ""
        if len(t) < 4 or "edittext" in n["cls"].lower(): continue
        if any(s in t.lower() for s in skip) and len(t) < 50: continue
        msgs.append((n["cy"], t))
    msgs.sort()
    return msgs[-1][1] if msgs else ""

def open_grok():
    shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
    time.sleep(0.45)

def inject(task, force_paste=False):
    open_grok()
    if not clip_set(task):
        return False, "clip_fail", None
    xml = dump_xml()
    if len(xml) < 120:
        return False, "dump_empty", None
    ns = parse(xml)
    comp = composer(ns)
    w, h = wm_size()
    if not comp:
        comp = {"cx": w//2, "cy": int(h*0.9), "x2": w//2}
    if force_paste or not task_visible(ns, comp, task):
        shell(f"input tap {comp['cx']} {comp['cy']}")
        time.sleep(0.12)
        shell("input keyevent 122")
        shell("input keyevent 279")
        time.sleep(0.22)
        log("inject paste279")
    else:
        log("inject skip_already_visible")
    xml2 = dump_xml()
    ns2 = parse(xml2)
    comp2 = composer(ns2) or comp
    if not task_visible(ns2, comp2, task):
        return False, "inject_not_visible", comp2
    return True, "inject_ok", comp2

def send(comp, ns=None):
    if ns is None:
        ns = parse(dump_xml())
    snd = send_node(ns, comp)
    if snd:
        shell(f"input tap {snd['cx']} {snd['cy']}")
        time.sleep(0.22)
        log(f"send tap {snd['cx']} {snd['cy']} {snd.get('src')}")
        (BRO/"meta/manual_send_tap.txt").write_text(f"{snd['cx']} {snd['cy']}\n", encoding="utf-8")
    shell(f"input tap {comp['cx']} {comp['cy']}")
    time.sleep(0.08)
    for _ in range(3):
        shell("input keyevent 66")
        time.sleep(0.18)
    log("send enter_x3")
    ns3 = parse(dump_xml())
    comp3 = composer(ns3) or comp
    if task_visible(ns3, comp3, os.environ.get("_LAST_TASK","")):
        if snd:
            shell(f"input tap {snd['cx']} {snd['cy']}")
            time.sleep(0.2)
        shell("input keyevent 66")
        log("send retry")
    return snd

def recv(before, max_s=None):
    max_s = float(max_s or os.environ.get("BROCCOLI_RECV_MAX", "28"))
    t0 = time.time()
    last = ""
    while time.time() - t0 < max_s:
        shell("input swipe 540 1500 540 800 220")
        time.sleep(0.1)
        ta = last_reply(parse(dump_xml()))
        if ta and ta != before and len(ta) >= 3:
            (BRO/"inbox/grok_reply.txt").write_text(ta, encoding="utf-8")
            log(f"recv ok len={len(ta)}")
            return ta
        if len(ta) > len(last): last = ta
        time.sleep(0.08)
    if last:
        (BRO/"inbox/grok_reply.txt").write_text(last, encoding="utf-8")
        log(f"recv partial len={len(last)}")
        return last
    log("recv timeout")
    return ""

def full_round(task):
    os.environ["_LAST_TASK"] = task
    task = task.strip()
    if not task:
        return {"ok": False, "error": "empty_task"}
    ok, st, comp = inject(task)
    if not ok:
        return {"ok": False, "stage": st}
    before = last_reply(parse(dump_xml()))
    snd = send(comp)
    reply = recv(before)
    success = bool(reply) and (len(reply) > 6 or "LOOP_OK" in reply)
    r = {"ok": success, "stage": "complete" if success else "recv", "send": snd, "reply_head": (reply or "")[:300]}
    (BRO/"meta/last_round.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    return r
