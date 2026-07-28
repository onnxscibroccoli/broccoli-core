#!/usr/bin/env python3
import json, re
from pathlib import Path
B = Path(__import__("os").environ.get("BROCCOLI_DIR", Path.home() / "broccoli"))
log = B / "god_mode_getevent.log"
if not log.is_file() or log.stat().st_size < 50:
    out = {"ok": False, "error": "empty log", "taps": [], "submit_keys": []}
    (B/"learned_inject.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out)); raise SystemExit(0)
text = log.read_text(errors="replace")
x = y = None
taps, keys = [], []
for line in text.splitlines():
    if "POSITION_X" in line or "0035" in line:
        m = re.search(r"([0-9a-f]+)\s*$", line, re.I)
        if m: x = int(m.group(1), 16)
    if "POSITION_Y" in line or "0036" in line:
        m = re.search(r"([0-9a-f]+)\s*$", line, re.I)
        if m: y = int(m.group(1), 16)
    if "BTN_TOUCH" in line and ("DOWN" in line.upper() or "00000001" in line):
        if x is not None and y is not None:
            taps.append({"x": x, "y": y})
    if "KEY_TAB" in line: keys.append({"key": "TAB", "code": 61})
    if "KEY_ENTER" in line or "KEY_KPENTER" in line: keys.append({"key": "ENTER", "code": 66})
dedup = []
for t in taps:
    if not dedup or (dedup[-1]["x"], dedup[-1]["y"]) != (t["x"], t["y"]):
        dedup.append(t)
out = {
    "ok": True,
    "taps": dedup[-8:],
    "submit_keys": keys[-10:],
    "use_tab_before_enter": any(k["key"]=="TAB" for k in keys) and any(k["key"]=="ENTER" for k in keys),
}
(B/"learned_inject.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
