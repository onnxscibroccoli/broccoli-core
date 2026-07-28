import os, re, time, subprocess
from broccoli_rish_shell import shell, wm_size
from broccoli_ui_dump import ui_dump, nodes, find_grok_search_box, composer_has_text

PREFIX = os.environ.get("PREFIX", "/data/data/com.termux/files/usr")

def clip_set(text):
    p = os.path.join(PREFIX, "bin", "termux-clipboard-set")
    if os.path.isfile(p):
        subprocess.run([p, text], timeout=8, check=False)
        return True
    return False

def clip_get():
    p = os.path.join(PREFIX, "bin", "termux-clipboard-get")
    if os.path.isfile(p):
        r = subprocess.run([p], capture_output=True, text=True, timeout=5)
        return (r.stdout or "").strip()
    return ""

def tap(x, y):
    shell(f"input tap {int(x)} {int(y)}")
    time.sleep(0.1)

def wait_for_search_box(pkg=None, max_s=6.0, poll=0.2):
    """Wait until Grok search/ask box appears (new task entry point)."""
    t0 = time.time()
    last = None
    while time.time() - t0 < max_s:
        xml = ui_dump()
        ns = nodes(xml)
        box = find_grok_search_box(ns, pkg)
        if box:
            return box, xml, time.time() - t0
        w, h = wm_size()
        tap(w // 2, int(h * 0.88))
        time.sleep(poll)
    xml = ui_dump()
    return find_grok_search_box(nodes(xml), pkg), xml, time.time() - t0

def inject_prompt(prompt, pkg=None):
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    w, h = wm_size()
    box, xml, dt_wait = wait_for_search_box(pkg, max_s=5.0)
    if not box:
        tap(w // 2, int(h * 0.9))
        time.sleep(0.3)
        xml = ui_dump()
        box = find_grok_search_box(nodes(xml), pkg)
    if not box:
        box = {"cx": w//2, "cy": int(h*0.9), "x1":0,"y1":0,"x2":w,"y2":h,"text":"","desc":""}

    tap(box["cx"], box["cy"])
    tap(box["cx"], box["cy"])
    time.sleep(0.12)
    shell("input keyevent 122")
    shell("input keyevent 67")  # DEL once — clear placeholder focus
    time.sleep(0.05)

    if not clip_set(prompt):
        safe = re.sub(r"[^a-zA-Z0-9 .,!?:_-]", "", prompt)[:180]
        shell("input text " + safe.replace(" ", "%s"))
    else:
        shell("input keyevent 279")
        time.sleep(0.12)
        xml2 = ui_dump()
        ns2 = nodes(xml2)
        box2 = find_grok_search_box(ns2, pkg) or box
        if not composer_has_text(ns2, box2, prompt):
            tap(box2["cx"], box2["cy"])
            shell("input keyevent 279")
            time.sleep(0.1)

    xml3 = ui_dump()
    ns3 = nodes(xml3)
    box3 = find_grok_search_box(ns3, pkg) or box
    ok = composer_has_text(ns3, box3, prompt) or prompt.strip()[:14] in clip_get()
    return ok, xml3, box3
