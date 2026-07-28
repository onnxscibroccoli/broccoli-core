import os, re, time, subprocess
from broccoli_rish_shell import shell, wm_size
from broccoli_ui_dump import ui_dump, nodes, find_grok_search_box, composer_has_text
from broccoli_strategy import log_path

PREFIX = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")

def clip_set(text):
    p = os.path.join(PREFIX, "bin", "termux-clipboard-set")
    if not os.path.isfile(p):
        log_path("inject", "clip_set_missing", False)
        return False
    subprocess.run([p, text], timeout=8, check=False)
    time.sleep(0.06)
    g = os.path.join(PREFIX, "bin", "termux-clipboard-get")
    if os.path.isfile(g):
        r = subprocess.run([g], capture_output=True, text=True, timeout=5)
        got = (r.stdout or "").strip()
        ok = text.strip()[:20] in got or got == text.strip()
        log_path("inject", "clip_set_verify", ok, {"len": len(text)})
        return ok or True
    log_path("inject", "clip_set", True)
    return True

def clip_get():
    p = os.path.join(PREFIX, "bin", "termux-clipboard-get")
    if os.path.isfile(p):
        r = subprocess.run([p], capture_output=True, text=True, timeout=5)
        return (r.stdout or "").strip()
    return ""

def tap(x, y):
    shell(f"input tap {int(x)} {int(y)}")
    time.sleep(0.08)

def wait_for_search_box(pkg=None, max_s=4.0):
    t0 = time.time()
    while time.time() - t0 < max_s:
        xml = ui_dump()
        ns = nodes(xml)
        box = find_grok_search_box(ns, pkg)
        if box:
            return box, xml, time.time() - t0
        w, h = wm_size()
        tap(w // 2, int(h * 0.88))
        time.sleep(0.15)
    xml = ui_dump()
    return find_grok_search_box(nodes(xml), pkg), xml, time.time() - t0

def inject_prompt(prompt, pkg=None):
    """ORDER: clip_set FIRST -> focus -> single PASTE (279) -> verify."""
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    if not clip_set(prompt):
        log_path("inject", "inject_fail_no_clip", False)
        return False, ui_dump(), None

    w, h = wm_size()
    box, xml, _ = wait_for_search_box(pkg, max_s=4.0)
    if not box:
        tap(w // 2, int(h * 0.9))
        time.sleep(0.2)
        box = find_grok_search_box(nodes(ui_dump()), pkg)
    if not box:
        box = {"cx": w//2, "cy": int(h*0.9), "x1":0,"y1":0,"x2":w,"y2":h}

    tap(box["cx"], box["cy"])
    time.sleep(0.1)
    shell("input keyevent 122")
    shell("input keyevent 279")
    time.sleep(0.14)

    xml2 = ui_dump()
    ns2 = nodes(xml2)
    box2 = find_grok_search_box(ns2, pkg) or box
    ok = composer_has_text(ns2, box2, prompt)
    if not ok and prompt.strip()[:16] in clip_get():
        ok = True
    log_path("inject", "paste_once_279", ok)
    return ok, xml2, box2
