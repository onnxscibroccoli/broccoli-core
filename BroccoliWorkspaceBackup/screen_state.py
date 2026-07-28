#!/usr/bin/env python3
import json, re, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
B = Path(__import__("os").environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
PKG, dump = "ai.x.grok", B / "window_dump.xml"

def fg_pkg():
    try:
        r = subprocess.run(["bash", str(B/"rish.sh"), "-c",
            "dumpsys activity activities 2>/dev/null|grep topResumedActivity|head -1"],
            capture_output=True, text=True, timeout=8)
        m = re.search(r"(\S+)/\S+", (r.stdout or "") + (r.stderr or ""))
        return m.group(1) if m else "unknown"
    except Exception:
        return "unknown"

fg = fg_pkg()
st = {"fg_package": fg, "on_grok": PKG in fg, "screen": "unknown", "can_inject": False,
      "chat_text_input": False, "has_ask_anything": False, "has_send": False,
      "input_xy": None, "send_xy": None}
if not dump.is_file() or dump.stat().st_size < 200:
    st["screen"] = "no_ui_dump"; print(json.dumps(st, indent=2)); raise SystemExit(0)
text = dump.read_text(errors="replace")
if PKG not in text:
    st["screen"] = "not_grok_ui"; print(json.dumps(st, indent=2)); raise SystemExit(0)
root = ET.parse(dump).getroot()
BLOCK = ("voice", "grok voice", "new chat", "images selector")

def bds(s):
    m = list(map(int, re.findall(r"\d+", s or "")))
    return (m[0], m[1], m[2], m[3]) if len(m) >= 4 else None

send_c = []
for el in root.iter("node"):
    if PKG not in (el.attrib.get("package") or PKG): continue
    rid, t = el.attrib.get("resource-id") or "", (el.attrib.get("text") or "").strip()
    if "chat_text_input" in rid:
        st["chat_text_input"] = True
        b = bds(el.attrib.get("bounds", ""))
        if b: st["input_xy"] = [(b[0]+b[2])//2, (b[1]+b[3])//2]
    if t == "Ask anything": st["has_ask_anything"] = True
    if el.attrib.get("clickable") != "true": continue
    b = bds(el.attrib.get("bounds", ""))
    if not b: continue
    cx, cy = (b[0]+b[2])//2, (b[1]+b[3])//2
    if cy < 2000: continue
    lab = (el.attrib.get("text") or el.attrib.get("content-desc") or "")
    low = lab.lower()
    if any(x in low for x in BLOCK): continue
    if "send" in low or ("message" in low and "send" in low):
        send_c.append((cy, cx, cy, lab))
if send_c:
    send_c.sort(reverse=True); _, x, y, _ = send_c[0]
    st["has_send"], st["send_xy"] = True, [x, y]
if st["chat_text_input"] or st["has_ask_anything"]:
    st["screen"], st["can_inject"] = "grok_chat_composer", True
elif "Grok Voice" in text: st["screen"] = "grok_voice_or_empty_bar"
elif "Log in" in text: st["screen"] = "grok_login"
else: st["screen"] = "grok_other"
print(json.dumps(st, indent=2))
