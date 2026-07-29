#!/usr/bin/env python3
import os, sys, json, time, subprocess, re, xml.etree.ElementTree as ET
from pathlib import Path

BRO = Path.home() / "broccoli"
sys.path.insert(0, str(BRO / "lib"))
GROK = os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
PREFIX = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")

from broccoli_rish_shell import shell, rish_ok, rish_path, wm_size

report = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "steps": [], "ok": False, "fixes": []}

def step(name, fn):
    try:
        r = fn()
        report["steps"].append({"name": name, "ok": True, "detail": r})
        print(f"OK  {name}: {str(r)[:200]}")
        return r
    except Exception as e:
        report["steps"].append({"name": name, "ok": False, "error": str(e)})
        print(f"FAIL {name}: {e}")
        return None

def clip_test():
    cs = Path(PREFIX) / "bin/termux-clipboard-set"
    cg = Path(PREFIX) / "bin/termux-clipboard-get"
    if not cs.is_file():
        return {"clip": False, "hint": "pkg install termux-api + enable Termux:API in Android"}
    subprocess.run([str(cs), "HEAL_CLIP_TEST"], timeout=8, check=False)
    got = subprocess.run([str(cg)], capture_output=True, text=True, timeout=5)
    return {"clip": "HEAL_CLIP_TEST" in (got.stdout or ""), "set": str(cs)}

def dump_test():
    remote = "/data/local/tmp/broccoli_ui.xml"
    cmds = [
        f"uiautomator dump --compressed {remote} 2>&1; echo RC=$?; wc -c {remote} 2>&1; head -c 200 {remote} 2>&1",
        f"cmd uiautomator dump {remote} 2>&1; echo RC=$?; wc -c {remote} 2>&1",
    ]
    best = ""
    for c in cmds:
        rc, out = shell(c, timeout=20)
        if "<?xml" in out:
            i = out.find("<?xml")
            best = out[i:i+500000]
            break
        # cat separate
        rc2, cat = shell(f"cat {remote} 2>/dev/null", timeout=10)
        if "<?xml" in cat:
            best = cat[cat.find("<?xml"):]
            break
    path = BRO / "ui/heal_dump.xml"
    if len(best) > 100:
        path.write_text(best[:2_000_000], encoding="utf-8")
    nodes = 0
    grok_nodes = 0
    if best:
        try:
            root = ET.fromstring(best.encode("utf-8", errors="replace"))
            for el in root.iter("node"):
                nodes += 1
                if GROK in (el.get("package") or ""):
                    grok_nodes += 1
        except ET.ParseError as e:
            return {"dump_bytes": len(best), "parse_error": str(e)}
    return {"dump_bytes": len(best), "nodes": nodes, "grok_nodes": grok_nodes, "saved": str(path)}

def input_test():
    w, h = wm_size()
    cx, cy = w // 2, int(h * 0.5)
    rc1, o1 = shell(f"input tap {cx} {cy}")
    time.sleep(0.2)
    rc2, o2 = shell("input keyevent 3")  # HOME
    time.sleep(0.3)
    return {"tap_rc": rc1, "home_rc": rc2, "tap_at": [cx, cy], "out": (o1 + o2)[:300]}

def open_grok_test():
    rc, out = shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
    time.sleep(0.6)
    rc2, out2 = shell(f"dumpsys window | grep -E 'mCurrentFocus|mFocusedApp' | head -3")
    return {"monkey_rc": rc, "focus": out2.strip()[:400], "grok_pkg": GROK}

def live_automation_probe():
    """Visible chain: open grok -> dump -> clip -> tap composer -> paste -> log send candidates"""
    task = "HEAL_PROBE reply PONG"
    cs = Path(PREFIX) / "bin/termux-clipboard-set"
    if cs.is_file():
        subprocess.run([str(cs), task], timeout=8, check=False)
    shell(f"monkey -p {GROK} -c android.intent.category.LAUNCHER 1")
    time.sleep(0.7)
    d = dump_test()
    if d.get("dump_bytes", 0) < 200:
        return {"automation": False, "reason": "EMPTY_UI_DUMP", "fix": "Enable USB debugging / grant shell; or use Shizuku; dump must work"}

    xml = (BRO / "ui/heal_dump.xml").read_text(encoding="utf-8", errors="replace")
    root = ET.fromstring(xml.encode("utf-8", errors="replace"))
    comp = None
    best_sc = -1
    w, h = wm_size()
    for el in root.iter("node"):
        if GROK not in (el.get("package") or ""):
            continue
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", el.get("bounds") or "")
        if not m: continue
        x1,y1,x2,y2 = map(int, m.groups())
        cls = el.get("class") or ""
        blob = ((el.get("text") or "") + (el.get("content-desc") or "")).lower()
        sc = 0
        if "EditText" in cls: sc += 80
        if any(k in blob for k in ("ask", "search", "message")): sc += 20
        sc += (y1+y2)//2 // 30
        if sc > best_sc:
            best_sc, comp = sc, ((x1+x2)//2, (y1+y2)//2, x2, (y1+y2)//2)

    if not comp:
        comp = (w//2, int(h*0.9), w-100, int(h*0.9))
        comp_reason = "fallback_bottom"
    else:
        comp_reason = "dump_edittext"

    cx, cy, x2, cy2 = comp
    shell(f"input tap {cx} {cy}")
    time.sleep(0.15)
    shell("input keyevent 122")
    shell("input keyevent 279")
    time.sleep(0.25)

    d2 = dump_test()
    sends = []
    xml2 = (BRO / "ui/heal_dump.xml").read_text(encoding="utf-8", errors="replace") if (BRO/"ui/heal_dump.xml").exists() else ""
    if xml2:
        root2 = ET.fromstring(xml2.encode("utf-8", errors="replace"))
        for el in root2.iter("node"):
            if GROK not in (el.get("package") or ""): continue
            if el.get("clickable") != "true": continue
            m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", el.get("bounds") or "")
            if not m: continue
            x1,y1,x2n,y2 = map(int, m.groups())
            ccx, ccy = (x1+x2n)//2, (y1+y2)//2
            if abs(ccy - cy2) > 120 or ccx <= x2 - 15: continue
            sends.append({"cx": ccx, "cy": ccy, "rid": el.get("resource-id"), "desc": el.get("content-desc"), "cls": el.get("class")})
        sends.sort(key=lambda s: -s["cx"])

    if sends:
        s0 = sends[0]
        shell(f"input tap {s0['cx']} {s0['cy']}")
        (BRO / "meta/manual_send_tap.txt").write_text(f"{s0['cx']} {s0['cy']}\n", encoding="utf-8")
        time.sleep(0.2)
    shell(f"input tap {cx} {cy}")
    shell("input keyevent 66")

    return {
        "automation": True,
        "composer": {"cx": cx, "cy": cy, "via": comp_reason},
        "paste": "keyevent_279",
        "send_candidates": sends[:6],
        "send_tapped": sends[0] if sends else None,
        "dump_after": d2,
    }

# run
step("rish_path", lambda: rish_path())
ok_r, rish_out = rish_ok()
step("rish_shell", lambda: {"ok": ok_r, "out": rish_out})
step("wm_size", lambda: wm_size())
step("clipboard", clip_test)
step("open_grok", open_grok_test)
step("ui_dump", dump_test)
step("input_inject", input_test)
probe = step("live_probe", live_automation_probe)

report["rish_ok"] = ok_r
report["probe"] = probe
report["ok"] = ok_r and (probe or {}).get("automation") is True

out = BRO / "reports/heal_debug_last.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
(BRO / "reports/heal_debug_last.log").write_text(
    "\n".join(f"{s['name']}: {'OK' if s.get('ok') else 'FAIL'} {s.get('error','')}" for s in report["steps"]),
    encoding="utf-8",
)

print("\n=== SUMMARY ===")
print(json.dumps({"rish_ok": ok_r, "probe_ok": report["ok"], "report": str(out)}, indent=2))

if not ok_r:
    print("\nFIX: termux-setup-storage; Settings → Apps → Termux → allow; run: rish -c whoami")
if probe and probe.get("reason") == "EMPTY_UI_DUMP":
    print("\nFIX: UI dump empty — automation cannot see Send/composer.")
    print("  - Same user/session as adb shell / Shizuku")
    print("  - Try: cmd uiautomator dump (in report)")
    print("  - MIUI/Samsung: disable battery restrict on Termux")
if probe and probe.get("send_candidates") == []:
    print("\nFIX: No send node in dump — after probe, manual send once; save tap from composer_row")
