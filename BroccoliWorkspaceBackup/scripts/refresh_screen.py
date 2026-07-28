#!/usr/bin/env python3
"""Proper dump then screen_state — use after inject."""
import json, os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def refresh():
    subprocess.run(["bash", os.path.join(ROOT, "ui_snapshot.sh")],
                     cwd=ROOT, capture_output=True, timeout=20)
    r = subprocess.run(["python3", os.path.join(ROOT, "screen_state.py")],
                       capture_output=True, text=True, timeout=15, cwd=ROOT)
    try:
        return json.loads(r.stdout or "{}")
    except Exception:
        return {}

def send_xy_from_dump():
    """Parse window_dump.xml for Send / submit clickable bounds."""
    import re
    for path in (
        os.path.join(ROOT, "window_dump.xml"),
        "/sdcard/broccoli_window_dump.xml",
    ):
        if not os.path.isfile(path):
            continue
        xml = open(path, encoding="utf-8", errors="ignore").read()
        best = None
        for line in xml.splitlines():
            low = line.lower()
            if not any(k in low for k in ("send", "submit", "arrow", "post")):
                continue
            if "clickable=\"false\"" in low and "send" in low:
                continue
            m = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', line)
            if m:
                x1, y1, x2, y2 = map(int, m.groups())
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                # prefer right side of composer (send is usually right of input)
                if cx > 700:
                    best = (cx, cy, line[:120])
        if best:
            return best[0], best[1], best[2]
    return None, None, None

def send_xy_from_profile():
    p = os.path.join(ROOT, "chat_profile.json")
    if not os.path.isfile(p):
        return None, None
    j = json.load(open(p, encoding="utf-8"))
    for key in ("send", "send_button"):
        o = j.get(key)
        if o and "x" in o and "y" in o:
            return int(o["x"]), int(o["y"])
    return None, None

if __name__ == "__main__":
    st = refresh()
    print(json.dumps({
        "state": st,
        "send_xy_state": st.get("send_xy"),
        "has_send": st.get("has_send"),
        "profile_xy": send_xy_from_profile(),
        "dump_xy": send_xy_from_dump()[:2],
    }, indent=2))
