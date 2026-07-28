import os, time
from broccoli_rish_shell import shell, wm_size
from broccoli_ui_dump import ui_dump, nodes, find_send, find_all_send_candidates, composer_has_text, find_grok_search_box
from broccoli_strategy import log_path, best_send_method

def tap_send_button(ns, pkg):
    sends = find_all_send_candidates(ns, pkg)
    for i, snd in enumerate(sends[:3]):
        shell(f"input tap {snd['cx']} {snd['cy']}")
        time.sleep(0.12)
        xml = ui_dump()
        ns2 = nodes(xml)
        box = find_grok_search_box(ns2, pkg)
        if box and not composer_has_text(ns2, box, "") or True:
            log_path("send", f"tap_send_{i}", True, {"cx": snd["cx"], "cy": snd["cy"], "rid": snd.get("rid")})
            return True, f"tap_send_{i}", xml
    return False, None, xml if 'xml' in dir() else ui_dump()

def send_enter():
    shell("input keyevent 66")
    time.sleep(0.1)
    log_path("send", "keyevent_66", True)
    return True, "keyevent_66", ui_dump()

def send_near_composer(ns, pkg):
    w, h = wm_size()
    box = find_grok_search_box(ns, pkg)
    if box:
        tx = min(w - 40, box["x2"] + 60)
        ty = box["cy"]
        shell(f"input tap {int(tx)} {int(ty)}")
        time.sleep(0.1)
        log_path("send", "tap_right_of_box", True, {"cx": tx, "cy": ty})
        return True, "tap_right_of_box", ui_dump()
    shell(f"input tap {w-80} {int(h*0.88)}")
    time.sleep(0.1)
    log_path("send", "tap_bottom_right", True)
    return True, "tap_bottom_right", ui_dump()

def auto_send(pkg=None, xml_before=None):
    pkg = pkg or os.environ.get("BROCCOLI_GROK_PKG", "ai.x.grok")
    methods = []
    pref = best_send_method()
    if pref:
        methods.append(pref)
    methods += ["tap_send_0", "tap_send_1", "keyevent_66", "tap_right_of_box", "tap_bottom_right"]

    seen = []
    for m in methods:
        if m in seen: continue
        seen.append(m)
        xml = xml_before or ui_dump()
        ns = nodes(xml)
        if m.startswith("tap_send"):
            ok, name, xml2 = tap_send_button(ns, pkg)
        elif m == "keyevent_66":
            ok, name, xml2 = send_enter()
        elif m in ("tap_right_of_box", "tap_bottom_right"):
            ok, name, xml2 = send_near_composer(ns, pkg)
        else:
            snd = find_send(ns, pkg)
            if snd:
                shell(f"input tap {snd['cx']} {snd['cy']}")
                time.sleep(0.1)
                ok, name, xml2 = True, "find_send", ui_dump()
            else:
                ok, name, xml2 = False, m, xml
        if ok:
            return True, name, xml2
    log_path("send", "all_failed", False)
    return False, None, ui_dump()
